from pydantic import BaseModel
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
from typing import Optional

class CreditAccountBase(BaseModel):
    credit_limit: float
    current_balance: float

class CreditAccountCreate(CreditAccountBase):
    farmer_id: int

class CreditAccountUpdate(BaseModel):
    credit_limit: Optional[float] = None
    current_balance: Optional[float] = None

class CreditAccount(TimestampSchema, CreditAccountBase):
    id: int
    farmer_id: int
    created_by: int

class CreditRepaymentBase(BaseModel):
    amount: float
    repayment_method: str

class CreditRepaymentCreate(CreditRepaymentBase):
    credit_account_id: int

class CreditRepayment(TimestampSchema, CreditRepaymentBase):
    id: int
    credit_account_id: int
    recorded_by: int