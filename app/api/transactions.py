from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from decimal import Decimal
from app.db.session import get_db
from app.models.transaction import (
    #User, Product, Produce, 
    Transaction, TransactionItem, Commission
)
from app.models.user import User
from app.models.product import Product
from app.models.produce import Produce
from app.models.credit import CreditAccount
from app.schemas.transaction import (
    Transaction, TransactionCreate, TransactionItem, CommissionBase
)
from app.auth.security import get_current_active_user, is_admin, is_salesperson, is_farmer

router = APIRouter()

# Commission rate (5%)
COMMISSION_RATE = Decimal('0.05')

@router.post("/", response_model=Transaction)
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Validate transaction type and user role
    if transaction.transaction_type == "product_purchase":
        if current_user.role not in ["farmer", "salesperson"]:
            raise HTTPException(
                status_code=403,
                detail="Only farmers and salespersons can create product purchases"
            )
    elif transaction.transaction_type == "produce_sale":
        if current_user.role != "salesperson":
            raise HTTPException(
                status_code=403,
                detail="Only salespersons can record produce sales"
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid transaction type")
    
    # Calculate total amount from items
    total_amount = Decimal('0')
    items_to_create = []
    
    for item in transaction.items:
        if transaction.transaction_type == "product_purchase":
            # For product purchases, verify product exists and has enough stock
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with ID {item.product_id} not found"
                )
            if product.quantity_in_stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough stock for product {product.name}"
                )
            
            item.unit_price = product.price
            total_amount += Decimal(str(item.quantity)) * Decimal(str(product.price))
            
            # Prepare item for creation
            items_to_create.append({
                "product_id": product.id,
                "quantity": item.quantity,
                "unit_price": product.price
            })
            
            # Update product stock
            product.quantity_in_stock -= item.quantity
            db.add(product)
        
        elif transaction.transaction_type == "produce_sale":
            # For produce sales, verify produce exists and is available
            produce = db.query(Produce).filter(Produce.id == item.produce_id).first()
            if not produce:
                raise HTTPException(
                    status_code=404,
                    detail=f"Produce with ID {item.produce_id} not found"
                )
            if not produce.is_available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Produce {produce.name} is not available"
                )
            
            item.unit_price = produce.price_per_unit
            total_amount += Decimal(str(item.quantity)) * Decimal(str(produce.price_per_unit))
            
            # Prepare item for creation
            items_to_create.append({
                "produce_id": produce.id,
                "quantity": item.quantity,
                "unit_price": produce.price_per_unit
            })
            
            # Mark produce as sold
            produce.is_available = False
            produce.quantity = 0  # Assuming all quantity is sold
            db.add(produce)
    
    # Verify payment method
    if transaction.payment_method == "credit":
        if current_user.role != "farmer":
            raise HTTPException(
                status_code=403,
                detail="Only farmers can purchase on credit"
            )
        
        # Check credit account
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.farmer_id == current_user.id
        ).first()
        
        if not credit_account:
            raise HTTPException(
                status_code=400,
                detail="No credit account exists for this farmer"
            )
        
        available_credit = credit_account.credit_limit - credit_account.current_balance
        if Decimal(str(total_amount)) > available_credit:
            raise HTTPException(
                status_code=400,
                detail="Insufficient credit limit for this purchase"
            )
        
        # Update credit balance
        credit_account.current_balance += Decimal(str(total_amount))
        db.add(credit_account)
    
    # Create transaction
    db_transaction = Transaction(
        transaction_type=transaction.transaction_type,
        user_id=current_user.id,
        amount=float(total_amount),
        payment_method=transaction.payment_method,
        status=transaction.status,
        notes=transaction.notes
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    # Create transaction items
    for item_data in items_to_create:
        db_item = TransactionItem(
            transaction_id=db_transaction.id,
            **item_data
        )
        db.add(db_item)
    
    # For produce sales, create commission record
    if transaction.transaction_type == "produce_sale":
        commission_amount = Decimal(str(total_amount)) * COMMISSION_RATE
        admin_user = db.query(User).filter(User.role == "admin").first()
        
        if admin_user:
            db_commission = Commission(
                transaction_id=db_transaction.id,
                amount=float(commission_amount),
                commission_rate=float(COMMISSION_RATE),
                beneficiary_id=admin_user.id
            )
            db.add(db_commission)
    
    db.commit()
    return db_transaction

@router.get("/", response_model=List[Transaction])
def read_transactions(
    skip: int = 0,
    limit: int = 100,
    transaction_type: str = None,
    user_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Transaction)
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if user_id:
        # Only admin can filter by other users
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        query = query.filter(Transaction.user_id == user_id)
    elif current_user.role != "admin":
        # Non-admin users can only see their own transactions
        query = query.filter(Transaction.user_id == current_user.id)
    
    if start_date:
        query = query.filter(Transaction.created_at >= start_date)
    if end_date:
        query = query.filter(Transaction.created_at <= end_date)
    
    transactions = query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    return transactions

@router.get("/{transaction_id}", response_model=Transaction)
def read_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Only admin or the user who created the transaction can see it
    if current_user.role != "admin" and current_user.id != db_transaction.user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return db_transaction