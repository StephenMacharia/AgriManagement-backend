from typing import Optional
from app.schemas.base import BaseSchema, TimestampSchema

class ProductBase(BaseSchema):
    name: str
    description: Optional[str] = None
    category: str
    price: float
    quantity_in_stock: int
    unit: str
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    quantity_in_stock: Optional[int] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None

class Product(TimestampSchema, ProductBase):
    id: int
    created_by: int