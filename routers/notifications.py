"""Notificaciones y alertas."""
import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Equipment, Invoice, InvoiceStatus, Part
from main import get_current_user, templates

router = APIRouter()


@router.get("")
def notifications_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    warranty_expiring = db.query(Equipment).filter(
        Equipment.warranty_until.isnot(None),
        Equipment.warranty_until <= (datetime.date.today() + datetime.timedelta(days=30))
    ).all()
    overdue = db.query(Invoice).filter(
        Invoice.status == InvoiceStatus.PENDING,
        Invoice.due_date.isnot(None),
        Invoice.due_date < datetime.date.today()
    ).count()
    low_stock = db.query(Part).filter(Part.stock <= Part.min_stock).all()
    return templates.TemplateResponse("notifications/index.html", {
        "request": request, "user": user,
        "warranty_expiring": warranty_expiring,
        "overdue_invoices": overdue,
        "low_stock_parts": low_stock
    })
