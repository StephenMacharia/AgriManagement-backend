from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.db.session import get_db
from app.models.user import User
from sqlalchemy import func
from app.models.transaction import Commission
from app.schemas.transaction import Commission
from app.auth.security import get_current_active_user, is_admin

router = APIRouter()

@router.get("/", response_model=List[Commission])
def read_commissions(
    skip: int = 0,
    limit: int = 100,
    start_date: datetime = None,
    end_date: datetime = None,
    beneficiary_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    query = db.query(Commission)
    
    if beneficiary_id:
        query = query.filter(Commission.beneficiary_id == beneficiary_id)
    
    if start_date:
        query = query.filter(Commission.created_at >= start_date)
    if end_date:
        query = query.filter(Commission.created_at <= end_date)
    
    commissions = query.order_by(Commission.created_at.desc()).offset(skip).limit(limit).all()
    return commissions

@router.get("/summary")
def get_commission_summary(
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    query = db.query(
        func.sum(Commission.amount).label("total_amount"),
        func.sum(Commission.amount / Commission.commission_rate).label("total_sales")
    )
    
    if start_date:
        query = query.filter(Commission.created_at >= start_date)
    if end_date:
        query = query.filter(Commission.created_at <= end_date)
    
    result = query.first()
    
    return {
        "total_commissions": result.total_amount if result.total_amount else 0,
        "total_sales": result.total_sales if result.total_sales else 0,
        "commission_rate": "5%"
    }