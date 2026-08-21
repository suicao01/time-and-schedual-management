from datetime import datetime
from langchain_core.tools import tool
from model import Events
from config import SessionLocal
from uuid import UUID

@tool
def delete_event(
    id: UUID) -> str:
    """Delete event with id"""

    with SessionLocal() as session:

        event = session.get(Events, id)

        if event is None:
            return f"Event {event.id} not found"
        
        session.delete(event)
        session.commit()
        return f"Event {event.id} deleted successfully."