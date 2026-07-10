"""Órdenes de Trabajo routes."""
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import (
    WorkOrder, WorkOrderPart, WorkOrderStatus, Equipment, EquipmentStatus,
    Client, User, Part, PartMovement, MovementType, ShopSettings, Estimate
)
from main import get_current_user, templates

router = APIRouter()


def _next_order_number(db):
    settings = db.query(ShopSettings).first()
    if not settings:
        return "OT-0001"
    num = settings.next_order or 1
    prefix = settings.order_prefix or "OT-"
    settings.next_order = num + 1
    db.commit()
    return f"{prefix}{num:04d}"


@router.get("")
def list_orders(
    request: Request,
    status: str = "",
    search: str = "",
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = db.query(WorkOrder).join(Client)
    if status:
        query = query.filter(WorkOrder.status == WorkOrderStatus(status))
    if search:
        query = query.filter(
            WorkOrder.order_number.ilike(f"%{search}%") |
            Client.name.ilike(f"%{search}%")
        )
    orders = query.order_by(WorkOrder.created_at.desc()).all()
    return templates.TemplateResponse("workorders/list.html", {
        "request": request, "user": user, "orders": orders,
        "search": search, "status": status,
        "statuses": list(WorkOrderStatus)
    })


@router.get("/nuevo")
def new_order(request: Request, client_id: int = 0, equip_id: int = 0, estimate_id: int = 0,
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    clients = db.query(Client).order_by(Client.name).all()
    technicians = db.query(User).filter(User.active == True).order_by(User.full_name).all()
    parts = db.query(Part).order_by(Part.name).all()
    equipment = db.query(Equipment).filter(
        Equipment.status.in_([EquipmentStatus.PENDING, EquipmentStatus.IN_REPAIR])
    ).all()
    return templates.TemplateResponse("workorders/form.html", {
        "request": request, "user": user,
        "clients": clients, "technicians": technicians, "parts": parts,
        "equipment": equipment,
        "selected_client_id": client_id,
        "selected_equip_id": equip_id,
        "estimate_id": estimate_id,
        "statuses": list(WorkOrderStatus),
        "today": datetime.date.today().isoformat()
    })


@router.post("/nuevo")
async def create_order(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    form = await request.form()
    equip_id = int(form.get("equipment_id", 0))
    equip = db.query(Equipment).filter(Equipment.id == equip_id).first()

    wo = WorkOrder(
        order_number=_next_order_number(db),
        client_id=int(form.get("client_id")),
        equipment_id=equip_id,
        technician_id=int(form.get("technician_id")) if form.get("technician_id") else None,
        estimate_id=int(form.get("estimate_id")) if form.get("estimate_id") else None,
        status=WorkOrderStatus.DIAGNOSIS,
        diagnosis=form.get("diagnosis"),
        labor_rate=float(form.get("labor_rate", 0)),
        internal_notes=form.get("internal_notes"),
        start_date=datetime.datetime.utcnow(),
        estimated_end_date=form.get("estimated_end_date") or None,
    )
    db.add(wo)
    db.commit()
    db.refresh(wo)

    # Update equipment status
    if equip:
        equip.status = EquipmentStatus.IN_REPAIR
        db.commit()

    return RedirectResponse(url=f"/ordenes/{wo.id}", status_code=303)


@router.get("/{order_id}")
def view_order(request: Request, order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404)
    parts = db.query(Part).order_by(Part.name).all()
    technicians = db.query(User).filter(User.active == True).all()
    return templates.TemplateResponse("workorders/view.html", {
        "request": request, "user": user, "order": order,
        "parts": parts, "technicians": technicians,
        "statuses": list(WorkOrderStatus)
    })


@router.post("/{order_id}/status")
async def update_status(request: Request, order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404)
    form = await request.form()
    new_status = form.get("status")
    if new_status:
        order.status = WorkOrderStatus(new_status)
        if new_status == WorkOrderStatus.DELIVERED.value:
            order.completed_date = datetime.datetime.utcnow()
            equip = db.query(Equipment).filter(Equipment.id == order.equipment_id).first()
            if equip:
                equip.status = EquipmentStatus.DELIVERED
                equip.delivery_date = datetime.datetime.utcnow()
        elif new_status in (WorkOrderStatus.IN_REPAIR.value, WorkOrderStatus.TESTING.value):
            equip = db.query(Equipment).filter(Equipment.id == order.equipment_id).first()
            if equip:
                equip.status = EquipmentStatus(new_status.replace("En Reparación", "En Reparación").replace("Pruebas", "Pruebas"))
                db.commit()
    db.commit()
    return RedirectResponse(url=f"/ordenes/{order_id}", status_code=303)


@router.post("/{order_id}/add-part")
async def add_part(request: Request, order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404)
    form = await request.form()
    part_id = int(form.get("part_id"))
    quantity = int(form.get("quantity", 1))
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404)

    # Add to work order
    wo_part = WorkOrderPart(
        work_order_id=order_id,
        part_id=part_id,
        quantity=quantity,
        unit_cost=part.cost_price,
        unit_price=part.sale_price
    )
    db.add(wo_part)

    # Reduce stock
    part.stock = max(0, part.stock - quantity)
    db.add(PartMovement(
        part_id=part_id,
        movement_type=MovementType.OUT,
        quantity=quantity,
        reference=order.order_number,
        notes=f"Usado en {order.order_number}",
        created_by=user.id
    ))
    db.commit()
    return RedirectResponse(url=f"/ordenes/{order_id}", status_code=303)


@router.post("/{order_id}/update-labor")
async def update_labor(request: Request, order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404)
    form = await request.form()
    order.labor_hours = float(form.get("labor_hours", 0))
    order.labor_rate = float(form.get("labor_rate", order.labor_rate))
    order.diagnosis = form.get("diagnosis", order.diagnosis)
    order.resolution = form.get("resolution", order.resolution)
    order.internal_notes = form.get("internal_notes", order.internal_notes)
    order.technician_id = int(form.get("technician_id")) if form.get("technician_id") else order.technician_id
    db.commit()
    return RedirectResponse(url=f"/ordenes/{order_id}", status_code=303)


@router.post("/{order_id}/eliminar")
def delete_order(order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if order:
        db.delete(order)
        db.commit()
    return RedirectResponse(url="/ordenes", status_code=303)
