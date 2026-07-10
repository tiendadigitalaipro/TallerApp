"""Equipos routes."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Equipment, EquipmentType, EquipmentStatus, Client, WorkOrder
from main import get_current_user, templates

router = APIRouter()


@router.get("")
def list_equipment(
    request: Request,
    search: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = db.query(Equipment).join(Client)
    if search:
        query = query.filter(
            Equipment.brand.ilike(f"%{search}%") |
            Equipment.model.ilike(f"%{search}%") |
            Equipment.serial_number.ilike(f"%{search}%") |
            Client.name.ilike(f"%{search}%")
        )
    if status:
        query = query.filter(Equipment.status == EquipmentStatus(status))
    equipment = query.order_by(Equipment.created_at.desc()).all()
    return templates.TemplateResponse("equipment/list.html", {
        "request": request, "user": user, "equipment": equipment,
        "search": search, "status": status,
        "statuses": list(EquipmentStatus)
    })


@router.get("/nuevo")
def new_equipment(request: Request, client_id: int = 0, db: Session = Depends(get_db), user=Depends(get_current_user)):
    clients = db.query(Client).order_by(Client.name).all()
    return templates.TemplateResponse("equipment/form.html", {
        "request": request, "user": user,
        "equipment": None, "clients": clients, "selected_client_id": client_id,
        "equipment_types": list(EquipmentType)
    })


@router.post("/nuevo")
async def create_equipment(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    form = await request.form()
    equip = Equipment(
        client_id=int(form.get("client_id")),
        equipment_type=EquipmentType(form.get("equipment_type")),
        brand=form.get("brand"),
        model=form.get("model"),
        serial_number=form.get("serial_number"),
        year=int(form.get("year", 0)) if form.get("year") else None,
        initial_diagnosis=form.get("initial_diagnosis"),
        status=EquipmentStatus.PENDING,
        estimated_delivery=form.get("estimated_delivery") or None,
        notes=form.get("notes"),
    )
    db.add(equip)
    db.commit()
    return RedirectResponse(url=f"/equipos/{equip.id}", status_code=303)


@router.get("/{equip_id}")
def view_equipment(request: Request, equip_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    equip = db.query(Equipment).filter(Equipment.id == equip_id).first()
    if not equip:
        raise HTTPException(status_code=404)
    work_orders = db.query(WorkOrder).filter(WorkOrder.equipment_id == equip_id).order_by(WorkOrder.created_at.desc()).all()
    return templates.TemplateResponse("equipment/view.html", {
        "request": request, "user": user, "equip": equip, "work_orders": work_orders,
        "statuses": list(EquipmentStatus)
    })


@router.post("/{equip_id}/status")
async def update_status(request: Request, equip_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    equip = db.query(Equipment).filter(Equipment.id == equip_id).first()
    if not equip:
        raise HTTPException(status_code=404)
    form = await request.form()
    new_status = form.get("status")
    if new_status:
        equip.status = EquipmentStatus(new_status)
        if new_status == EquipmentStatus.DELIVERED.value:
            equip.delivery_date = __import__("datetime").datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/equipos/{equip_id}", status_code=303)


@router.post("/{equip_id}/eliminar")
def delete_equipment(equip_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    equip = db.query(Equipment).filter(Equipment.id == equip_id).first()
    if equip:
        db.delete(equip)
        db.commit()
    return RedirectResponse(url="/equipos", status_code=303)
