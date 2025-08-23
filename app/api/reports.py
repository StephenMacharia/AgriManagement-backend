from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.db.session import get_db
from app.models.transaction import (
     Transaction, Commission,TransactionItem
)
from app.models.user import User
from app.models.credit import CreditAccount
from app.models.product import Product
from app.models.produce import Produce

from app.auth.security import get_current_active_user, is_admin

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_reports(
    time_range: str = "month",  # day, week, month, year
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    # Calculate date ranges
    end_date = datetime.utcnow()
    
    if time_range == "day":
        start_date = end_date - timedelta(days=1)
    elif time_range == "week":
        start_date = end_date - timedelta(weeks=1)
    elif time_range == "month":
        start_date = end_date - timedelta(days=30)
    elif time_range == "year":
        start_date = end_date - timedelta(days=365)
    else:
        raise HTTPException(status_code=400, detail="Invalid time range")
    
    # Active users count
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    
    # Total products sold
    product_sales = db.query(
        func.sum(TransactionItem.quantity),
        func.sum(TransactionItem.quantity * TransactionItem.unit_price)
    ).join(Transaction).filter(
        Transaction.transaction_type == "product_purchase",
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).first()
    
    # Total produce sold
    produce_sales = db.query(
        func.sum(TransactionItem.quantity),
        func.sum(TransactionItem.quantity * TransactionItem.unit_price)
    ).join(Transaction).filter(
        Transaction.transaction_type == "produce_sale",
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).first()
    
    # Total commissions
    total_commissions = db.query(func.sum(Commission.amount)).filter(
        Commission.created_at >= start_date,
        Commission.created_at <= end_date
    ).scalar() or 0
    
    # Credit statistics
    credit_stats = db.query(
        func.sum(CreditAccount.credit_limit).label("total_limit"),
        func.sum(CreditAccount.current_balance).label("total_balance")
    ).first()
    
    return {
        "time_range": time_range,
        "start_date": start_date,
        "end_date": end_date,
        "active_users": active_users,
        "product_sales": {
            "quantity": product_sales[0] if product_sales[0] else 0,
            "amount": product_sales[1] if product_sales[1] else 0
        },
        "produce_sales": {
            "quantity": produce_sales[0] if produce_sales[0] else 0,
            "amount": produce_sales[1] if produce_sales[1] else 0
        },
        "total_commissions": total_commissions,
        "credit_stats": {
            "total_limit": credit_stats.total_limit if credit_stats.total_limit else 0,
            "total_balance": credit_stats.total_balance if credit_stats.total_balance else 0,
            "available_credit": (credit_stats.total_limit - credit_stats.total_balance) 
                if credit_stats.total_limit and credit_stats.total_balance else 0
        }
    }