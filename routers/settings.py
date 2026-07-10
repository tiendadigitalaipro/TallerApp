"""Configuración del taller."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import ShopSettings
from main import get_current_user, templates

router = APIRouter()


@router.get("")
def view_settings(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    settings = db.query(ShopSettings).first()
    return templates.TemplateResponse("settings/form.html", {"request": request, "user": user, "settings": settings})


@router.post("")
async def save_settings(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    settings = db.query(ShopSettings).first()
    if not settings:
        settings = ShopSettings()
        db.add(settings)
    form = await request.form()
    for field in ['shop_name', 'address', 'phone', 'email', 'website', 'invoice_prefix', 'estimate_prefix', 'order_prefix', 'whatsapp_number', 'currency']:
        val = form.get(field)
        if val is not None: setattr(settings, field, val)
    for field in ['tax_rate', 'labor_rate']:
        val = form.get(field)
        if val is not None: setattr(settings, field, float(val))
    settings.social_media = {"instagram": form.get("instagram"), "facebook": form.get("facebook")}
    db.commit()
    return RedirectResponse(url="/configuracion", status_code=303)
