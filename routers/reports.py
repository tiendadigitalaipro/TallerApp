"""Reportes y análisis."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Equipment, WorkOrder, WorkOrderStatus, Part, WorkOrderPart, User, Invoice, InvoiceStatus, Client
from main import get_current_user, templates

router = APIRouter()


@router.get("")
def reports_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    repairs_by_type = db.query(
        Equipment.equipment_type, func.count(WorkOrder.id)
    ).join(WorkOrder, WorkOrder.equipment_id == Equipment.id
    ).group_by(Equipment.equipment_type).all()

    top_parts = db.query(
        Part.name, func.coalesce(func.sum(WorkOrderPart.quantity), 0).label('usage_count')
    ).outerjoin(WorkOrderPart, WorkOrderPart.part_id == Part.id
    ).group_by(Part.id, Part.name
    ).order_by(func.coalesce(func.sum(WorkOrderPart.quantity), 0).desc()
    ).limit(10).all()

    tech_perf = db.query(
        User.full_name,
        func.count(WorkOrder.id).label('total'),
        func.coalesce(func.avg(WorkOrder.labor_hours), 0).label('avg_hours')
    ).join(WorkOrder, WorkOrder.technician_id == User.id
    ).filter(WorkOrder.status == WorkOrderStatus.DELIVERED
    ).group_by(User.id).all()

    return templates.TemplateResponse("reports/index.html", {
        "request": request, "user": user, "repairs_by_type": repairs_by_type,
        "top_parts": top_parts, "tech_perf": tech_perf
    })
