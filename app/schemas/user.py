from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.schemas.base import BaseSchema, TimestampSchema

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = "farmer"  # Default role

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None

class UserInDB(TimestampSchema, UserBase):
    id: int
    role: str
    is_active: bool
    
    # Add this configuration
    model_config = ConfigDict(from_attributes=True)

class User(UserInDB):
    pass

# 🔑 Fix: Make UserWithToken include a `user` object + tokens
class UserWithToken(BaseModel):
    user: User
    access_token: str
    token_type: str
    
    # Add this configuration
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None