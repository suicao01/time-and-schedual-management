from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from fastapi.responses import StreamingResponse
import json
from .agents.orchestrator import ask_agent, close_mcp_stack, initialize_mcp_stack
from config import close_checkpointer, get_db, initialize_checkpointer, engine, Base
from . import model, schema
from langchain_core.messages import BaseMessage
@asynccontextmanager
async def lifespan(_app: FastAPI):
    await initialize_checkpointer()
    await initialize_mcp_stack()
    try:
        yield
    finally:
        await close_mcp_stack()
        await close_checkpointer()


app = FastAPI(title="Booking API", lifespan=lifespan)




@app.post(
    "/users",
    response_model=schema.UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    user: schema.UserCreate,
    db: Session = Depends(get_db)
):
    new_user = model.User(
        name=user.name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.post(
    "/hotels",
    response_model=schema.HotelResponse,
    status_code=status.HTTP_201_CREATED
)
def create_hotel(
    hotel: schema.HotelCreate,
    db: Session = Depends(get_db)
):
    new_hotel = model.Hotel(
        name=hotel.name,
        description=hotel.description,
        location=hotel.location
    )

    db.add(new_hotel)
    db.commit()
    db.refresh(new_hotel)

    return new_hotel


@app.post(
    "/hotels",
    response_model=schema.HotelResponse,
    status_code=status.HTTP_201_CREATED
)
def create_hotel(
    hotel: schema.HotelCreate,
    db: Session = Depends(get_db)
):
    new_hotel = model.Hotel(
        name=hotel.name,
        description=hotel.description,
        location=hotel.location
    )

    db.add(new_hotel)
    db.commit()
    db.refresh(new_hotel)

    return new_hotel

@app.post(
    "/events",
    response_model=schema.EventResponse,
    status_code=status.HTTP_201_CREATED
)
def create_event(
    event: schema.EventCreate,
    db: Session = Depends(get_db)
):
    new_event = model.Events(
       
        description=event.description,
        start_date = event.start_date,
        end_date = event.end_date,
        tags  = event.tags
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event



 
@app.post("/ask")
async def ask(payload: schema.AskRequest):
   
    result =  await ask_agent(
        question=payload.question,
        user_id=str(payload.user_id),
        session_id=payload.session_id,
    )
    return result
 
 
# @app.post("/resume")
# async def resume(payload: schema.ResumeRequest):
#     result = await resume_agent(
#         interrupt_id=payload.interrupt_id,
#         user_id=payload.user_id,
#         session_id=payload.session_id,
#         approved=payload.approved,
#         reason=payload.reason,
#         input = payload.input
#     )
#     return result

def _json_default(obj):
  
    if isinstance(obj, BaseMessage):
        return {
            "type": obj.type,
            "content": obj.content,
            "name": getattr(obj, "name", None),
            "tool_calls": getattr(obj, "tool_calls", None),
            "tool_call_id": getattr(obj, "tool_call_id", None),
            "additional_kwargs": getattr(obj, "additional_kwargs", None),
        }
 
    # Pydantic v2 model (BaseModel) - ví dụ state object nào đó
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            pass
 
    
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
 
    # Fallback cuối cùng: ép sang string để không bao giờ crash stream
    return str(obj)
 

def _safe_dumps(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False, default=_json_default)
 

# @app.post("/ask/stream")
# async def ask_stream(req: schema.AskRequest):
#     async def event_generator():
#         try:
#             async for event in ask_agent_stream(
#                 question=req.question,
#                 user_id=req.user_id,
#                 session_id=req.session_id,
#             ):
#                 # SSE format
#                 yield f"data: {_safe_dumps(event)}\n\n"
#         except Exception as e:
#             error_event = {"type": "error", "message": str(e)}
#             yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
 
#     return StreamingResponse(
#         event_generator(),
#         media_type="text/event-stream",
#     )