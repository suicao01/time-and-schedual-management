from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True) 

class UserCreate(BaseSchema):
    name: str


class UserResponse(BaseSchema):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class HotelCreate(BaseSchema):
    name: str
    description: str
    location: str


class HotelResponse(BaseSchema):
    id: UUID
    name: str
    description: str
    location: str

    class Config:
        from_attributes = True
        
class EventCreate(BaseSchema):
    description : str
    start_date : datetime
    end_date: datetime
    tags: Optional[list[str]] = None
    
    
class EventResponse(BaseSchema):
    id : UUID
    start_date: datetime
    end_date: datetime
    description: str
    tags: Optional[list[str]] = None
    class Config:
                from_attributes = True

class EventUpdate(BaseSchema):
    id : UUID
    description : str| None
    start_date : datetime | None
    end_date: datetime | None
    tags : list[str] | None
    class Config:
            from_attributes = True
        
        
class QuestionRequest(BaseSchema):
    question: str
    session_id : Optional[str] |None
    user_id:str
    
    
class QuestionResponse(BaseSchema):
    answer: str
    session_id : str
    
    
class AskRequest(BaseModel):
    question: str
    user_id: UUID
    session_id: str | None = None
 
 
class ResumeRequest(BaseModel):
    user_id: str
    session_id: str          
    approved: bool
    interrupt_id : str
    reason: str | None = None
    input : str|None = None
 
