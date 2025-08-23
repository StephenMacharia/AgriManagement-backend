from typing import Optional
from pydantic import BaseModel
from app.schemas.base import BaseSchema, TimestampSchema

class ProduceBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    quantity: float
    unit: str
    price_per_unit: float
    image_url: Optional[str] = None

class ProduceCreate(ProduceBase):
    pass

class ProduceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[float] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None

class Produce(TimestampSchema, ProduceBase):
    id: int
    farmer_id: int
    is_available: bool