"""Presupuestos / Estimates routes."""
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import (
    Estimate, EstimateItem, EstimateStatus, Client, Equipment,
    User, ShopSettings, Part, EquipmentType
)
from main import get_current_user, templates

router = APIRouter()


def _next_estimate_number(db):
    settings = db.query(ShopSettings).first()
    if not settings:
        return "PRE-0001"
    num = settings.next_estimate or 1
    prefix = settings.estimate_prefix or "PRE-"
    settings.next_estimate = num + 1
    db.commit()
    return f"{prefix}{num:04d}"


@router.get("")
def list_estimates(request: Request, status: str = "", search: str = "",
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(Estimate).join(Client)
    if status:
        query = query.filter(Estimate.status == EstimateStatus(status))
    if search:
        query = query.filter(
            Estimate.estimate_number.ilike(f"%{search}%") |
            Client.name.ilike(f"%{search}%")
        )
    estimates = query.order_by(Estimate.created_at.desc()).all()
    return templates.TemplateResponse("estimates/list.html", {
        "request": request, "user": user, "estimates": estimates,
        "search": search, "status": status,
        "statuses": list(EstimateStatus)
    })


@router.get("/nuevo")
def new_estimate(request: Request, client_id: int = 0, equip_id: int = 0,
                 db: Session = Depends(get_db), user=Depends(get_current_user)):
    clients = db.query(Client).order_by(Client.name).all()
    parts = db.query(Part).order_by(Part.name).all()
    settings = db.query(ShopSettings).first()
    tax_rate = settings.tax_rate if settings else 16.0
    equipment = db.query(Equipment).all()
    return templates.TemplateResponse("estimates/form.html", {
        "request": request, "user": user, "estimate": None,
        "clients": clients, "parts": parts, "equipment": equipment,
        "selected_client_id": client_id, "selected_equip_id": equip_id,
        "tax_rate": tax_rate, "today": datetime.date.today().isoformat()
    })


@router.post("/nuevo")
async def create_estimate(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    form = await request.form()
    items_data = []
    i = 0
    while True:
        desc = form.get(f"items[{i}][description]")
        if desc is None:
            break
        qty = int(form.get(f"items[{i}][quantity]", 1))
        price = float(form.get(f"items[{i}][unit_price]", 0))
        items_data.append({"description": desc, "quantity": qty, "unit_price": price, "item_type": form.get(f"items[{i}][item_type]", "part")})
        i += 1

    subtotal = sum(item["quantity"] * item["unit_price"] for item in items_data)
    tax_rate = float(form.get("tax_rate", 16))
    discount = float(form.get("discount", 0))
    discount_type = form.get("discount_type", "percent")

    if discount_type == "percent":
        discount_amount = subtotal * (discount / 100)
    else:
        discount_amount = discount

    taxable = subtotal - discount_amount
    tax_amount = taxable * (tax_rate / 100)
    total = taxable + tax_amount

    estimate = Estimate(
        estimate_number=_next_estimate_number(db),
        client_id=int(form.get("client_id")),
        equipment_id=int(form.get("equipment_id")) if form.get("equipment_id") else None,
        status=EstimateStatus.DRAFT,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        discount=discount,
        discount_type=discount_type,
        total=total,
        valid_until=form.get("valid_until") or None,
        notes=form.get("notes"),
        terms=form.get("terms"),
        created_by=user.id,
    )
    db.add(estimate)
    db.flush()

    for item in items_data:
        db.add(EstimateItem(
            estimate_id=estimate.id,
            item_type=item["item_type"],
            description=item["description"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total=item["quantity"] * item["unit_price"],
        ))
    db.commit()
    return RedirectResponse(url=f"/presupuestos/{estimate.id}", status_code=303)


@router.get("/{est_id}")
def view_estimate(request: Request, est_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    estimate = db.query(Estimate).filter(Estimate.id == est_id).first()
    if not estimate:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("estimates/view.html", {
        "request": request, "user": user, "estimate": estimate
    })


@router.post("/{est_id}/status")
async def update_status(request: Request, est_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    estimate = db.query(Estimate).filter(Estimate.id == est_id).first()
    if not estimate:
        raise HTTPException(status_code=404)
    form = await request.form()
    new_status = form.get("status")
    if new_status:
        estimate.status = EstimateStatus(new_status)
        if new_status == EstimateStatus.APPROVED.value:
            estimate.approved_at = datetime.datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/presupuestos/{est_id}", status_code=303)


@router.post("/{est_id}/convertir")
def convert_to_wo(est_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Convert approved estimate to work order."""
    from routers.workorders import _next_order_number
    from models import WorkOrder, WorkOrderStatus, Equipment, EquipmentStatus

    estimate = db.query(Estimate).filter(Estimate.id == est_id).first()
    if not estimate or estimate.status != EstimateStatus.APPROVED:
        raise HTTPException(status_code=400, detail="El presupuesto debe estar Aprobado")

    wo = WorkOrder(
        order_number=_next_order_number(db),
        client_id=estimate.client_id,
        equipment_id=estimate.equipment_id,
        estimate_id=estimate.id,
        status=WorkOrderStatus.DIAGNOSIS,
        estimated_end_date=estimate.valid_until,
        created_by=user.id,
    )
    db.add(wo)
    estimate.status = EstimateStatus.CONVERTED

    if estimate.equipment_id:
        equip = db.query(Equipment).filter(Equipment.id == estimate.equipment_id).first()
        if equip:
            equip.status = EquipmentStatus.IN_REPAIR
    db.commit()
    return RedirectResponse(url=f"/ordenes/{wo.id}", status_code=303)


@router.post("/{est_id}/eliminar")
def delete_estimate(est_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    est = db.query(Estimate).filter(Estimate.id == est_id).first()
    if est:
        db.delete(est)
        db.commit()
    return RedirectResponse(url="/presupuestos", status_code=303)
