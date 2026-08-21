from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True) 

class EventCreate(BaseSchema):
    description : str
    start_date : datetime
    end_date: datetime
    tags = list[str]
    
class EventUpdate(BaseSchema):
    id : UUID
    description : str| None
    start_date : datetime | None
    end_date: datetime | None
    tags = list[str] | None