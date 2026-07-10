"""Clientes CRM routes."""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Client, ClientInteraction, ClientDocument, User
from main import get_current_user, templates

router = APIRouter()


@router.get("")
def list_clients(request: Request, search: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(Client)
    if search:
        query = query.filter(
            Client.name.ilike(f"%{search}%") |
            Client.phone.ilike(f"%{search}%") |
            Client.email.ilike(f"%{search}%")
        )
    clients = query.order_by(Client.created_at.desc()).all()
    return templates.TemplateResponse("clients/list.html", {
        "request": request, "user": user, "clients": clients, "search": search
    })


@router.get("/nuevo")
def new_client(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("clients/form.html", {
        "request": request, "user": user, "client": None
    })


@router.post("/nuevo")
async def create_client(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    form = await request.form()
    client = Client(
        name=form.get("name"),
        phone=form.get("phone"),
        email=form.get("email"),
        address=form.get("address"),
        contact_preference=form.get("contact_preference", "WhatsApp"),
        notes=form.get("notes"),
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    # Log interaction
    if form.get("initial_notes"):
        db.add(ClientInteraction(
            client_id=client.id,
            interaction_type="Nota",
            notes=form.get("initial_notes"),
            created_by=user.id
        ))
        db.commit()

    return RedirectResponse(url="/clientes", status_code=303)


@router.get("/{client_id}")
def view_client(request: Request, client_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("clients/view.html", {
        "request": request, "user": user, "client": client
    })


@router.get("/{client_id}/editar")
def edit_client(request: Request, client_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("clients/form.html", {
        "request": request, "user": user, "client": client
    })


@router.post("/{client_id}/editar")
async def update_client(
    request: Request, client_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404)
    form = await request.form()
    client.name = form.get("name", client.name)
    client.phone = form.get("phone", client.phone)
    client.email = form.get("email", client.email)
    client.address = form.get("address", client.address)
    client.contact_preference = form.get("contact_preference", client.contact_preference)
    client.notes = form.get("notes", client.notes)
    db.commit()
    return RedirectResponse(url=f"/clientes/{client_id}", status_code=303)


@router.post("/{client_id}/interaccion")
async def add_interaction(
    request: Request, client_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    form = await request.form()
    interaction = ClientInteraction(
        client_id=client_id,
        interaction_type=form.get("interaction_type", "Nota"),
        notes=form.get("notes"),
        created_by=user.id
    )
    db.add(interaction)
    db.commit()
    return RedirectResponse(url=f"/clientes/{client_id}", status_code=303)


@router.post("/{client_id}/eliminar")
def delete_client(client_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client:
        db.delete(client)
        db.commit()
    return RedirectResponse(url="/clientes", status_code=303)
