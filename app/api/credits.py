from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from app.db.session import get_db
from app.models.credit import  CreditAccount, CreditRepayment
from app.models.user import User
from app.schemas.credit import (
    CreditAccount, CreditAccountCreate, CreditAccountUpdate,
    CreditRepayment, CreditRepaymentCreate
)
from app.auth.security import get_current_active_user, is_admin, is_salesperson

router = APIRouter()

@router.post("/accounts", response_model=CreditAccount)
def create_credit_account(
    credit_account: CreditAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    # Check if farmer exists and is actually a farmer
    farmer = db.query(User).filter(
        (User.id == credit_account.farmer_id) &
        (User.role == "farmer")
    ).first()
    
    if not farmer:
        raise HTTPException(
            status_code=404,
            detail="Farmer not found or user is not a farmer"
        )
    
    # Check if farmer already has a credit account
    existing_account = db.query(CreditAccount).filter(
        CreditAccount.farmer_id == credit_account.farmer_id
    ).first()
    
    if existing_account:
        raise HTTPException(
            status_code=400,
            detail="Farmer already has a credit account"
        )
    
    db_account = CreditAccount(
        farmer_id=credit_account.farmer_id,
        credit_limit=credit_account.credit_limit,
        current_balance=credit_account.current_balance,
        created_by=current_user.id
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/accounts", response_model=List[CreditAccount])
def read_credit_accounts(
    skip: int = 0,
    limit: int = 100,
    farmer_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(CreditAccount)
    
    if farmer_id:
        # Only admin can filter by other farmers
        if current_user.role != "admin" and current_user.id != farmer_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        query = query.filter(CreditAccount.farmer_id == farmer_id)
    elif current_user.role == "farmer":
        # Farmers can only see their own credit account
        query = query.filter(CreditAccount.farmer_id == current_user.id)
    elif current_user.role == "salesperson":
        # Salespersons can see all credit accounts
        pass
    # Admin can see all
    
    accounts = query.offset(skip).limit(limit).all()
    return accounts

@router.get("/accounts/{account_id}", response_model=CreditAccount)
def read_credit_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_account = db.query(CreditAccount).filter(CreditAccount.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Credit account not found")
    
    # Only admin, salesperson, or the account owner can see it
    if (current_user.role not in ["admin", "salesperson"] and 
        current_user.id != db_account.farmer_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return db_account

@router.put("/accounts/{account_id}", response_model=CreditAccount)
def update_credit_account(
    account_id: int,
    credit_account: CreditAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    db_account = db.query(CreditAccount).filter(CreditAccount.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Credit account not found")
    
    update_data = credit_account.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_account, field, update_data[field])
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.post("/repayments", response_model=CreditRepayment)
def create_credit_repayment(
    repayment: CreditRepaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_salesperson)
):
    # Verify credit account exists
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.id == repayment.credit_account_id
    ).first()
    
    if not credit_account:
        raise HTTPException(
            status_code=404,
            detail="Credit account not found"
        )
    
    # Verify repayment amount is positive
    if repayment.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount must be positive"
        )
    
    # Verify repayment doesn't exceed current balance
    if Decimal(str(repayment.amount)) > credit_account.current_balance:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount exceeds current balance"
        )
    
    # Create repayment record
    db_repayment = CreditRepayment(
        credit_account_id=repayment.credit_account_id,
        amount=repayment.amount,
        repayment_method=repayment.repayment_method,
        recorded_by=current_user.id
    )
    db.add(db_repayment)
    
    # Update credit account balance
    credit_account.current_balance -= Decimal(str(repayment.amount))
    db.add(credit_account)
    
    db.commit()
    db.refresh(db_repayment)
    return db_repayment

@router.get("/repayments", response_model=List[CreditRepayment])
def read_credit_repayments(
    skip: int = 0,
    limit: int = 100,
    account_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(CreditRepayment)
    
    if account_id:
        # Verify permissions
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.id == account_id
        ).first()
        
        if not credit_account:
            raise HTTPException(status_code=404, detail="Credit account not found")
        
        if (current_user.role not in ["admin", "salesperson"] and 
            current_user.id != credit_account.farmer_id):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        query = query.filter(CreditRepayment.credit_account_id == account_id)
    elif current_user.role == "farmer":
        # Farmers can only see their own repayments
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.farmer_id == current_user.id
        ).first()
        
        if credit_account:
            query = query.filter(
                CreditRepayment.credit_account_id == credit_account.id
            )
    
    repayments = query.order_by(CreditRepayment.created_at.desc()).offset(skip).limit(limit).all()
    return repayments