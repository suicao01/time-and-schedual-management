from datetime import datetime
from langchain_core.tools import tool

from model import Events
from config import SessionLocal
from uuid import UUID

@tool
def update_event(
    id: UUID,
    start_time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,) -> str:
    """Update event with one of these fields"""

    with SessionLocal() as session:

        event = session.get(Events, id)

        if event is None:
            return f"Event {id} not found."

        if start_time is not None:
            event.start_time = datetime.fromisoformat(start_time)

        if end_time is not None:
            event.end_time = datetime.fromisoformat(end_time)

        if (
            event.end_time <= event.start_time
        ):
            return "end_time must be after start_time."

        if description is not None:
            event.description = description

        if tags is not None:
            event.tags = tags

        session.commit()
        session.refresh(event)

        return f"Event {event.id} updated successfully."