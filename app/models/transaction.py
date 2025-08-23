from sqlalchemy import Column, Enum, Numeric, String, ForeignKey,Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Transaction(BaseModel):
    __tablename__ = "transactions"
    
    transaction_type = Column(Enum('product_purchase', 'produce_sale', name='transaction_types'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(Enum('cash', 'credit', 'mobile_money', name='payment_methods'), nullable=False)
    status = Column(Enum('pending', 'completed', 'failed', name='transaction_status'), default='completed')
    notes = Column(String)
    
    user = relationship("User")
    items = relationship("TransactionItem", back_populates="transaction")
    commission = relationship("Commission", uselist=False, back_populates="transaction")

class TransactionItem(BaseModel):
    __tablename__ = "transaction_items"
    
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))
    produce_id = Column(Integer, ForeignKey('produce.id'))
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    
    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product")
    produce = relationship("Produce")

class Commission(BaseModel):
    __tablename__ = "commissions"
    
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=False, unique=True)
    amount = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=False)
    beneficiary_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    transaction = relationship("Transaction", back_populates="commission")
    beneficiary = relationship("User")