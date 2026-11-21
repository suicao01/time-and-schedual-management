from datetime import datetime
from uuid import UUID

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select
from loguru import logger

from app.model import Events
from config import SessionLocal


def _get_user_id(config: RunnableConfig) -> str:
    return config["configurable"]["user_id"]


@tool()
def create_event(
    start_time: datetime,
    end_time: datetime,
    description: str,
    config: RunnableConfig,
    tags: list[str] | None = None,
) -> str:
    """Create a new event with a start time, end time, description and tags."""

    if end_time <= start_time:
        return "End time must be after start time."

    user_id = _get_user_id(config)

    with SessionLocal() as session:
        event = Events(
            start_time=start_time,
            end_time=end_time,
            description=description,
            tags=tags or [],
            user_id=user_id,
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


@tool()
def delete_event(id: UUID, config: RunnableConfig) -> str:
    """
    Delete one event by ID.
    Before deleting, use list_events to find the event ID.
    If the user asks to delete multiple events, call this tool
    once for each event ID that should be deleted.
    """

    user_id = _get_user_id(config)

    with SessionLocal() as session:
        stmt = select(Events).where(
            Events.id == id,
            Events.user_id == user_id,
        )

        event = session.scalar(stmt)

        if event is None:
            return f"Event {id} not found."

        session.delete(event)
        session.commit()

        return f"Event {id} deleted successfully."


@tool()
def update_event(
    id: UUID,
    config: RunnableConfig,
    start_time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Update an event."""

    user_id = _get_user_id(config)

    with SessionLocal() as session:
        stmt = select(Events).where(
            Events.id == id,
            Events.user_id == user_id,
        )

        event = session.scalar(stmt)

        if event is None:
            return f"Event {id} not found."

        if start_time is not None:
            event.start_time = datetime.fromisoformat(start_time)

        if end_time is not None:
            event.end_time = datetime.fromisoformat(end_time)

        if event.end_time <= event.start_time:
            return "end_time must be after start_time."

        if description is not None:
            event.description = description

        if tags is not None:
            event.tags = tags

        session.commit()
        session.refresh(event)

        return f"Event {id} updated successfully."


@tool()
def list_events(
    config: RunnableConfig,
    start_from: str | None = None,
    start_to: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """List events filtered by date and tags."""

    user_id = _get_user_id(config)

    with SessionLocal() as session:
        stmt = select(Events).where(Events.user_id == user_id)

        if start_from is not None:
            stmt = stmt.where(Events.start_time >= datetime.fromisoformat(start_from))

        if start_to is not None:
            stmt = stmt.where(Events.start_time <= datetime.fromisoformat(start_to))

        if tags:
            for tag in tags:
                stmt = stmt.where(Events.tags.any(tag))

        stmt = stmt.order_by(Events.start_time)

        events = session.scalars(stmt).all()

        if not events:
            return "No events found."

        result = []

        for event in events:
            result.append({
                "id": str(event.id),
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "description": event.description,
                "tags": event.tags or [],
            })

        logger.info(f"list_events result: {result}")

        return str(result)