from sqlalchemy import Column, String, Boolean, Enum
from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    phone_number = Column(String(20))
    role = Column(Enum('admin', 'salesperson', 'farmer', name='user_roles'), nullable=False)
    is_active = Column(Boolean, default=True)