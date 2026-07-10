"""Facturación routes."""
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Invoice, InvoiceItem, InvoiceStatus, Client, WorkOrder, User, ShopSettings
from main import get_current_user, templates

router = APIRouter()


def _next_invoice_number(db):
    settings = db.query(ShopSettings).first()
    if not settings: return "FAC-0001"
    num = settings.next_invoice or 1
    prefix = settings.invoice_prefix or "FAC-"
    settings.next_invoice = num + 1
    db.commit()
    return f"{prefix}{num:04d}"


@router.get("")
def list_invoices(request: Request, status: str = "", search: str = "",
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(Invoice).join(Client)
    if status: query = query.filter(Invoice.status == InvoiceStatus(status))
    if search: query = query.filter(Invoice.invoice_number.ilike(f"%{search}%") | Client.name.ilike(f"%{search}%"))
    invoices = query.order_by(Invoice.created_at.desc()).all()
    return templates.TemplateResponse("invoices/list.html", {
        "request": request, "user": user, "invoices": invoices, "search": search, "status": status,
        "statuses": list(InvoiceStatus)
    })


@router.get("/nuevo")
def new_invoice(request: Request, order_id: int = 0, db: Session = Depends(get_db), user=Depends(get_current_user)):
    clients = db.query(Client).order_by(Client.name).all()
    orders = db.query(WorkOrder).filter(WorkOrder.status.notin_(["Cancelado"])).all() if hasattr(WorkOrder.status, 'notin_') else db.query(WorkOrder).all()
    settings = db.query(ShopSettings).first()
    return templates.TemplateResponse("invoices/form.html", {
        "request": request, "user": user, "invoice": None,
        "clients": clients, "orders": orders,
        "selected_order_id": order_id,
        "tax_rate": settings.tax_rate if settings else 16.0,
        "today": datetime.date.today().isoformat()
    })


@router.post("/nuevo")
async def create_invoice(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    form = await request.form()
    items_data = []
    i = 0
    while True:
        desc = form.get(f"items[{i}][description]")
        if desc is None: break
        qty = int(form.get(f"items[{i}][quantity]", 1))
        price = float(form.get(f"items[{i}][unit_price]", 0))
        items_data.append({"description": desc, "quantity": qty, "unit_price": price})
        i += 1
    subtotal = sum(it["quantity"] * it["unit_price"] for it in items_data)
    tax_rate = float(form.get("tax_rate", 16))
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount

    inv = Invoice(
        invoice_number=_next_invoice_number(db),
        client_id=int(form.get("client_id")),
        work_order_id=int(form.get("work_order_id")) if form.get("work_order_id") else None,
        status=InvoiceStatus.PENDING,
        subtotal=subtotal, tax_rate=tax_rate, tax_amount=tax_amount, total=total,
        due_date=form.get("due_date") or None,
        notes=form.get("notes"), created_by=user.id,
    )
    db.add(inv)
    db.flush()
    for item in items_data:
        db.add(InvoiceItem(invoice_id=inv.id, description=item["description"], quantity=item["quantity"], unit_price=item["unit_price"], total=item["quantity"]*item["unit_price"]))
    db.commit()
    return RedirectResponse(url=f"/facturas/{inv.id}", status_code=303)


@router.get("/{inv_id}")
def view_invoice(request: Request, inv_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    invoice = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not invoice: raise HTTPException(status_code=404)
    return templates.TemplateResponse("invoices/view.html", {"request": request, "user": user, "invoice": invoice})


@router.post("/{inv_id}/pagar")
async def pay_invoice(request: Request, inv_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not inv: raise HTTPException(status_code=404)
    form = await request.form()
    amount = float(form.get("amount", inv.total))
    inv.amount_paid += amount
    if inv.amount_paid >= inv.total:
        inv.status = InvoiceStatus.PAID
        inv.paid_at = datetime.datetime.utcnow()
    else:
        inv.status = InvoiceStatus.PARTIAL
    db.commit()
    return RedirectResponse(url=f"/facturas/{inv_id}", status_code=303)


@router.post("/{inv_id}/eliminar")
def delete_invoice(inv_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if inv: db.delete(inv); db.commit()
    return RedirectResponse(url="/facturas", status_code=303)
