"""Usuarios y roles."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserRole
from main import get_current_user, templates, hash_password

router = APIRouter()


@router.get("")
def list_users(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != UserRole.ADMIN: raise HTTPException(status_code=403)
    users = db.query(User).order_by(User.full_name).all()
    return templates.TemplateResponse("settings/users.html", {"request": request, "user": user, "users": users, "roles": list(UserRole)})


@router.post("/nuevo")
async def create_user(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != UserRole.ADMIN: raise HTTPException(status_code=403)
    form = await request.form()
    new_user = User(
        username=form.get("username"), full_name=form.get("full_name"),
        email=form.get("email"), phone=form.get("phone"),
        password_hash=hash_password(form.get("password", "123456")),
        role=UserRole(form.get("role")),
    )
    db.add(new_user); db.commit()
    return RedirectResponse(url="/usuarios", status_code=303)


@router.post("/{uid}/toggle")
def toggle_user(uid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != UserRole.ADMIN: raise HTTPException(status_code=403)
    target = db.query(User).filter(User.id == uid).first()
    if target: target.active = not target.active; db.commit()
    return RedirectResponse(url="/usuarios", status_code=303)
