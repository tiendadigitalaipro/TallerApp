"""TallerApp — Main application entry point."""
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import engine, Base, get_db, SessionLocal
from models import User, UserRole, ShopSettings

# ─── App Setup ──────────────────────────────────────────────────────────

app = FastAPI(title="TallerApp", version="1.0.0")

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Auth
SECRET_KEY = os.getenv("SECRET_KEY", "tallerapp-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 24  # hours
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ─── Auth Helpers ───────────────────────────────────────────────────────

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=303, headers={"Location": "/login"})
    except JWTError:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.active:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


# ─── Startup ────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Create default admin
    if not db.query(User).first():
        admin = User(
            username="admin",
            full_name="Administrador",
            email="admin@taller.com",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN
        )
        db.add(admin)
        db.commit()
    # Create default settings
    if not db.query(ShopSettings).first():
        db.add(ShopSettings())
        db.commit()
    db.close()


# ─── Auth Routes ────────────────────────────────────────────────────────

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, db: Session = Depends(get_db)):
    form = {}
    try:
        data = request.form()
        # handled via form
    except:
        pass
    from fastapi.responses import HTMLResponse
    return HTMLResponse("Use form", status_code=400)


@app.post("/api/login")
async def api_login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not user.active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response


# ─── Dashboard ──────────────────────────────────────────────────────────

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from models import WorkOrder, WorkOrderStatus, Equipment, Client, Invoice, InvoiceStatus, Estimate, Part
    from sqlalchemy import func

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_orders = db.query(func.count(WorkOrder.id)).filter(
        WorkOrder.status.in_([
            WorkOrderStatus.DIAGNOSIS, WorkOrderStatus.WAITING_PARTS,
            WorkOrderStatus.IN_REPAIR, WorkOrderStatus.TESTING, WorkOrderStatus.READY
        ])
    ).scalar() or 0

    completed_today = db.query(func.count(WorkOrder.id)).filter(
        WorkOrder.status == WorkOrderStatus.DELIVERED,
        WorkOrder.completed_date >= today_start
    ).scalar() or 0

    # Income today
    income_today = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(
        Invoice.status == InvoiceStatus.PAID,
        Invoice.paid_at >= today_start
    ).scalar() or 0

    # Income this month
    month_start = today_start.replace(day=1)
    income_month = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(
        Invoice.status == InvoiceStatus.PAID,
        Invoice.paid_at >= month_start
    ).scalar() or 0

    # Low stock parts
    low_stock = db.query(Part).filter(Part.stock <= Part.min_stock).count()

    # Warranty equipment
    warranty_count = db.query(func.count(Equipment.id)).filter(
        Equipment.warranty_until >= today_start.date()
    ).scalar() or 0

    # Recent orders
    recent_orders = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).limit(5).all()

    # Monthly income for chart (last 6 months)
    monthly_income = []
    for i in range(5, -1, -1):
        m_start = today_start.replace(day=1) - timedelta(days=30 * i)
        if i > 0:
            m_end = today_start.replace(day=1) - timedelta(days=30 * (i - 1))
        else:
            m_end = now
        total = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_at >= m_start,
            Invoice.paid_at < m_end
        ).scalar() or 0
        monthly_income.append({
            "month": m_start.strftime("%b"),
            "total": float(total)
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "active_orders": active_orders,
        "completed_today": completed_today,
        "income_today": float(income_today),
        "income_month": float(income_month),
        "low_stock": low_stock,
        "warranty_count": warranty_count,
        "total_clients": db.query(func.count(Client.id)).scalar() or 0,
        "total_equipment": db.query(func.count(Equipment.id)).scalar() or 0,
        "recent_orders": recent_orders,
        "monthly_income": monthly_income
    })


# ─── Register Routers ───────────────────────────────────────────────────

from routers import clients, equipment, inventory, workorders, estimates, invoices, bidding, notifications, settings, reports, users

app.include_router(clients.router, prefix="/clientes", tags=["Clientes"])
app.include_router(equipment.router, prefix="/equipos", tags=["Equipos"])
app.include_router(inventory.router, prefix="/inventario", tags=["Inventario"])
app.include_router(workorders.router, prefix="/ordenes", tags=["Órdenes de Trabajo"])
app.include_router(estimates.router, prefix="/presupuestos", tags=["Presupuestos"])
app.include_router(invoices.router, prefix="/facturas", tags=["Facturación"])
app.include_router(bidding.router, prefix="/licitaciones", tags=["Licitaciones"])
app.include_router(notifications.router, prefix="/notificaciones", tags=["Notificaciones"])
app.include_router(settings.router, prefix="/configuracion", tags=["Configuración"])
app.include_router(reports.router, prefix="/reportes", tags=["Reportes"])
app.include_router(users.router, prefix="/usuarios", tags=["Usuarios"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
