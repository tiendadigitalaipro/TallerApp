"""Licitaciones / Bidding routes."""
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Bid, BiddingStatus, User
from main import get_current_user, templates

router = APIRouter()


@router.get("")
def list_bids(request: Request, status: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(Bid)
    if status: query = query.filter(Bid.status == BiddingStatus(status))
    bids = query.order_by(Bid.created_at.desc()).all()
    return templates.TemplateResponse("bidding/list.html", {
        "request": request, "user": user, "bids": bids, "status": status,
        "statuses": list(BiddingStatus)
    })


@router.get("/nuevo")
def new_bid(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("bidding/form.html", {
        "request": request, "user": user, "bid": None, "today": datetime.date.today().isoformat()
    })


@router.post("/nuevo")
async def create_bid(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    form = await request.form()
    bid = Bid(
        title=form.get("title"), institution=form.get("institution"),
        reference=form.get("reference"), description=form.get("description"),
        estimated_value=float(form.get("estimated_value", 0)) or None,
        proposed_value=float(form.get("proposed_value", 0)) or None,
        status=BiddingStatus.IN_PROGRESS,
        submission_date=form.get("submission_date") or None,
        deadline=form.get("deadline") or None,
        notes=form.get("notes"), created_by=user.id,
    )
    db.add(bid); db.commit()
    return RedirectResponse(url=f"/licitaciones/{bid.id}", status_code=303)


@router.get("/{bid_id}")
def view_bid(request: Request, bid_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid: raise HTTPException(status_code=404)
    return templates.TemplateResponse("bidding/view.html", {"request": request, "user": user, "bid": bid})


@router.post("/{bid_id}/status")
async def update_status(request: Request, bid_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid: raise HTTPException(status_code=404)
    form = await request.form()
    new_status = form.get("status")
    if new_status: bid.status = BiddingStatus(new_status)
    if new_status == BiddingStatus.WON.value: bid.result_date = datetime.datetime.utcnow()
    if new_status == BiddingStatus.LOST.value: bid.result_date = datetime.datetime.utcnow()
    if form.get("proposed_value"): bid.proposed_value = float(form.get("proposed_value"))
    db.commit()
    return RedirectResponse(url=f"/licitaciones/{bid_id}", status_code=303)


@router.post("/{bid_id}/eliminar")
def delete_bid(bid_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if bid: db.delete(bid); db.commit()
    return RedirectResponse(url="/licitaciones", status_code=303)
