from pydantic import BaseModel
from datetime import datetime

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime