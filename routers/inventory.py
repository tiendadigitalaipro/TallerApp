"""Inventario de repuestos routes."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Part, PartMovement, PartCategory, MovementType, Supplier
from main import get_current_user, templates

router = APIRouter()


@router.get("")
def list_parts(
    request: Request,
    search: str = "",
    low_stock: bool = False,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = db.query(Part)
    if search:
        query = query.filter(
            Part.name.ilike(f"%{search}%") |
            Part.code.ilike(f"%{search}%") |
            Part.description.ilike(f"%{search}%")
        )
    if low_stock:
        query = query.filter(Part.stock <= Part.min_stock)
    parts = query.order_by(Part.name).all()
    return templates.TemplateResponse("inventory/list.html", {
        "request": request, "user": user, "parts": parts,
        "search": search, "low_stock": low_stock
    })


@router.get("/nuevo")
def new_part(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse("inventory/form.html", {
        "request": request, "user": user, "part": None, "suppliers": suppliers,
        "categories": list(PartCategory)
    })


@router.post("/nuevo")
async def create_part(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    form = await request.form()
    part = Part(
        code=form.get("code"),
        name=form.get("name"),
        description=form.get("description"),
        category=PartCategory(form.get("category")) if form.get("category") else PartCategory.OTHER,
        stock=int(form.get("stock", 0)),
        min_stock=int(form.get("min_stock", 5)),
        location=form.get("location"),
        cost_price=float(form.get("cost_price", 0)),
        sale_price=float(form.get("sale_price", 0)),
        supplier_id=int(form.get("supplier_id")) if form.get("supplier_id") else None,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    # Log initial stock movement
    if part.stock > 0:
        db.add(PartMovement(
            part_id=part.id,
            movement_type=MovementType.IN,
            quantity=part.stock,
            notes="Stock inicial",
            created_by=user.id
        ))
        db.commit()
    return RedirectResponse(url="/inventario", status_code=303)


@router.get("/{part_id}")
def view_part(request: Request, part_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404)
    movements = db.query(PartMovement).filter(PartMovement.part_id == part_id).order_by(PartMovement.created_at.desc()).limit(20).all()
    return templates.TemplateResponse("inventory/view.html", {
        "request": request, "user": user, "part": part, "movements": movements
    })


@router.post("/{part_id}/movimiento")
async def add_movement(request: Request, part_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404)
    form = await request.form()
    mtype = MovementType(form.get("movement_type"))
    qty = int(form.get("quantity", 0))
    movement = PartMovement(
        part_id=part_id,
        movement_type=mtype,
        quantity=qty,
        reference=form.get("reference"),
        notes=form.get("notes"),
        created_by=user.id
    )
    db.add(movement)
    if mtype == MovementType.IN:
        part.stock += qty
    elif mtype == MovementType.OUT:
        part.stock = max(0, part.stock - qty)
    db.commit()
    return RedirectResponse(url=f"/inventario/{part_id}", status_code=303)


@router.get("/proveedores")
def list_suppliers(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse("inventory/suppliers.html", {
        "request": request, "user": user, "suppliers": suppliers
    })


@router.post("/proveedores/nuevo")
async def create_supplier(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    form = await request.form()
    supplier = Supplier(
        name=form.get("name"),
        contact=form.get("contact"),
        phone=form.get("phone"),
        email=form.get("email"),
        delivery_time=form.get("delivery_time"),
        notes=form.get("notes"),
    )
    db.add(supplier)
    db.commit()
    return RedirectResponse(url="/inventario/proveedores", status_code=303)


@router.post("/{part_id}/eliminar")
def delete_part(part_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    part = db.query(Part).filter(Part.id == part_id).first()
    if part:
        db.delete(part)
        db.commit()
    return RedirectResponse(url="/inventario", status_code=303)
