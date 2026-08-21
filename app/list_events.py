from datetime import datetime
from langchain_core.tools import tool
from model import Events
from config import SessionLocal
from uuid import UUID
from sqlalchemy import select
@tool
def list_events(
    start_from : str | None = None,
    start_to : str | None = None,
    tags : list[str]| None = None,) -> str:
    """List event filter by date"""

    with SessionLocal() as session:

        stmt = select(Events)

        if start_from is not None:
            stmt = stmt.where(
                Events.start_time >= datetime.fromisoformat(start_from)
            )

        if start_to is not None:
            stmt = stmt.where(
                Events.start_time <= datetime.fromisoformat(start_to)
            )

        if tags is not None:
            stmt = stmt.where(
                Events.tags.any(tags)
            )

        stmt = stmt.order_by(Events.start_time)

        events = session.scalars(stmt).all()

        if not events:
            return "No events found."

        result = []

        for event in events:
            result.append(
                {
                    "id": str(event.id),
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat(),
                    "description": event.description,
                    "tags": event.tags or []
                }
            )

        return str(result)