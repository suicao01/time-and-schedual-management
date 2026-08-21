from datetime import datetime
from langchain_core.tools import tool
from fastapi import Depends

from model import Events
from config import SessionLocal
@tool
def create_event(start_time: datetime,end_time: datetime,description: str, tags : list[str] | None|None) -> str:
    """Create a new event with a title, start time, and end time."""
    start = datetime.isoformat(start_time)
    end = datetime.isoformat(end_time)
    
    if end <= start:
        return "End time must be after start time"
   
    with SessionLocal() as session:

        event = Events(
            start_time=start,
            end_time=end,
            description=description,
            tags=tags or []
        )

        session.add(event)
        session.commit()
        session.refresh(event)
    return (
            f"Event created successfully. "
            f"ID: {event.id}, "
            f"description: {event.description}, "
            f"start: {event.start_time}, "
            f"end: {event.end_time}"
        )
