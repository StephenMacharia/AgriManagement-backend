from sqlalchemy import Column, String, Integer, Enum, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Product(BaseModel):
    __tablename__ = "products"
    
    name = Column(String(100), nullable=False)
    description = Column(String)
    category = Column(Enum('seed', 'fertilizer', 'tool', 'pesticide', 'other', name='product_categories'), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    quantity_in_stock = Column(Integer, nullable=False, default=0)
    unit = Column(String(20), nullable=False)
    image_url = Column(String(255))
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    creator = relationship("User")