import argparse
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, or_, and_
from mcp.server.fastmcp import Context, FastMCP

from config import SessionLocal
from app.model import Booking, User, Hotel
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "hotel_booking",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost:*",
            "127.0.0.1:*",
            "192.168.50.85:*",   # IP LAN thật của máy chạy server
            "172.16.0.68:*",    # IP LAN ảo của máy chạy server (VM)
        ],
        allowed_origins=[
            "http://localhost:*",
            "http://127.0.0.1:*",
            "http://192.168.50.85:*",
            "http://172.16.0.68:*",
        ],
    ),
)


def _get_user_id_from_ctx(ctx: Context) -> UUID:
    request = ctx.request_context.request  # Starlette Request
    raw = request.headers.get("x-user-id")
    if not raw:
        raise ValueError("Missing x-user-id header")
    return UUID(raw)
    


# CURRENT_USER_ID: UUID = "4865a98e-3572-434f-8aa9-1f0eb089be0d" or _get_current_user_id()


def _parse_uuid(value: str, field_name: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


@mcp.tool()
def search_hotels(
    name: str | None = None,
    location: str | None = None,
    description: str | None = None,
    
) -> str:
    """Search hotels by location/description/name"""

    with SessionLocal() as session:
        query = select(Hotel)
        conditions = []
        if location:
            conditions.append(Hotel.location.ilike(f"%{location}%"))
        if name:
            conditions.append(Hotel.name.ilike(f"%{name}%"))
        if description:
            conditions.append(Hotel.description.ilike(f"%{description}%"))

        if conditions:
            query = query.where(or_(*conditions))

        hotels = session.scalars(query).all()

        if not hotels:
            return "No hotels found."

        result = [
            {
                "id": str(hotel.id),
                "name": hotel.name,
                "location": hotel.location,
                "description": hotel.description,
            }
            for hotel in hotels
        ]

    return str(result)


@mcp.tool()
def cancel_booking(booking_id: str, ctx: Context):
    """
    Delete booking based on booking_id. Chỉ cho phép xóa booking
    thuộc về chính user đang đăng nhập (CURRENT_USER_ID).
    """
    user_id = _get_user_id_from_ctx(ctx)
    booking_uuid = _parse_uuid(booking_id, "booking_id")
    if booking_uuid is None:
        return {
            "success": False,
            "message": f"Invalid booking_id: {booking_id!r}. It must be a valid UUID.",
        }

    db = SessionLocal()
    try:
        booking = db.get(Booking, booking_uuid)
        if not booking:
            return {"success": False, "message": "Booking not found"}

        if booking.user_id != user_id:
            return {"success": False, "message": "You cannot cancel this booking."}

        db.delete(booking)
        db.commit()

        return {
            "success": True,
            "message": "Delete booking successfully",
            "booking_id": booking_id,
        }
    finally:
        db.close()


@mcp.tool()
def create_booking(hotel_id: str, start_time: str, end_time: str, ctx: Context):
    """
    Create a hotel booking for the current authenticated user.
    """
    user_id = _get_user_id_from_ctx(ctx)
    hotel_uuid = _parse_uuid(hotel_id, "hotel_id")
    if hotel_uuid is None:
        return {
            "success": False,
            "message": f"Invalid hotel_id: {hotel_id!r}. It must be a valid UUID returned by search_hotels.",
        }

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        hotel = db.get(Hotel, hotel_uuid)

        if not user:
            return {"success": False, "message": "User not found."}

        if not hotel:
            return {"success": False, "message": "Hotel not found."}

        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
        except ValueError:
            return {
                "success": False,
                "message": "Invalid date format for start_time/end_time. Use ISO format, e.g. 2026-09-01T14:00:00.",
            }

        if start >= end:
            return {"success": False, "message": "Invalid booking time."}

        query = select(Booking).where(
            and_(
                Booking.hotel_id == hotel_uuid,
                Booking.start_time < end,
                Booking.end_time > start,
            )
        )

        existing_booking = db.execute(query).scalars().first()

        if existing_booking:
            return {
                "success": False,
                "message": "Hotel is already booked for this period.",
            }

        booking = Booking(
            user_id=user_id,
            hotel_id=hotel_uuid,
            start_time=start,
            end_time=end,
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        return {
            "success": True,
            "booking_id": str(booking.id),
            "hotel": hotel.name,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@mcp.tool()
def check_hotel_availability(hotel_id: str, start_time: str, end_time: str):
    """
    Check whether a hotel is available for the requested time range.
    """
    hotel_uuid = _parse_uuid(hotel_id, "hotel_id")
    if hotel_uuid is None:
        return {
            "available": False,
            "message": f"Invalid hotel_id: {hotel_id!r}. It must be a valid UUID returned by search_hotels.",
        }

    db = SessionLocal()
    try:
        hotel = db.get(Hotel, hotel_uuid)
        if not hotel:
            return {"available": False, "message": "Hotel not found."}

        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
        except ValueError:
            return {
                "available": False,
                "message": "Invalid date format for start_time/end_time. Use ISO format, e.g. 2026-09-01T14:00:00.",
            }

        if start >= end:
            return {"available": False, "message": "Invalid booking time."}

        query = select(Booking).where(
            and_(
                Booking.hotel_id == hotel_uuid,
                Booking.start_time < end,
                Booking.end_time > start,
            )
        )

        existing_booking = db.execute(query).scalars().first()

        if existing_booking:
            return {
                "available": False,
                "hotel_id": hotel_id,
                "hotel_name": hotel.name,
                "message": "Hotel is not available for this period.",
            }

        return {
            "available": True,
            "hotel_id": hotel_id,
            "hotel_name": hotel.name,
            "start_time": start_time,
            "end_time": end_time,
            "message": "Hotel is available.",
        }
    finally:
        db.close()


@mcp.tool()
def get_my_bookings(ctx: Context):
    """
    Get all bookings belonging to the current authenticated user.
    """
    user_id = _get_user_id_from_ctx(ctx)
    db = SessionLocal()
    try:
        query = select(Booking).where(Booking.user_id == user_id)
        bookings = db.execute(query).scalars().all()

        return [
            {
                "booking_id": str(booking.id),
                "hotel_id": str(booking.hotel_id),
                "hotel_name": booking.hotel.name,
                "location": booking.hotel.location,
                "start_time": booking.start_time.isoformat(),
                "end_time": booking.end_time.isoformat(),
            }
            for booking in bookings
        ]
    finally:
        db.close()


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8001
    mcp.run(transport="streamable-http")