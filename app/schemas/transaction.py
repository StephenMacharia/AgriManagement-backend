from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.product import Product
from app.schemas.produce import Produce

class TransactionItemBase(BaseModel):
    product_id: Optional[int] = None
    produce_id: Optional[int] = None
    quantity: float
    unit_price: float

class TransactionItemCreate(TransactionItemBase):
    pass

class TransactionItem(TransactionItemBase):
    id: int
    transaction_id: int
    product: Optional[Product] = None
    produce: Optional[Produce] = None

class TransactionBase(BaseModel):
    transaction_type: str
    amount: float
    payment_method: str
    status: Optional[str] = "completed"
    notes: Optional[str] = None

class TransactionCreate(TransactionBase):
    items: List[TransactionItemCreate]

class TransactionUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class Transaction(TimestampSchema, TransactionBase):
    id: int
    user_id: int
    items: List[TransactionItem]

class CommissionBase(BaseModel):
    amount: float
    commission_rate: float

class CommissionCreate(CommissionBase):
    transaction_id: int

class Commission(TimestampSchema, CommissionBase):
    id: int
    transaction_id: int
    beneficiary_id: int