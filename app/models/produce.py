from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey,Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Produce(BaseModel):
    __tablename__ = "produce"
    
    name = Column(String(100), nullable=False)
    description = Column(String)
    category = Column(String(50), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    price_per_unit = Column(Numeric(10, 2), nullable=False)
    farmer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_available = Column(Boolean, default=True)
    image_url = Column(String(255))
    
    farmer = relationship("User")