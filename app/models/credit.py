from sqlalchemy import Column, Numeric, ForeignKey,Integer,Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class CreditAccount(BaseModel):
    __tablename__ = "credit_accounts"
    
    farmer_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    credit_limit = Column(Numeric(10, 2), nullable=False)
    current_balance = Column(Numeric(10, 2), nullable=False, default=0)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    farmer = relationship("User", foreign_keys=[farmer_id])
    creator = relationship("User", foreign_keys=[created_by])

class CreditRepayment(BaseModel):
    __tablename__ = "credit_repayments"
    
    credit_account_id = Column(Integer, ForeignKey('credit_accounts.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    repayment_method = Column(Enum('cash', 'mobile_money', name='repayment_methods'), nullable=False)
    recorded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    credit_account = relationship("CreditAccount")
    recorder = relationship("User")