import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from config import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable = False)
    bookings = relationship("Booking", back_populates="user")
    events = relationship("Events", back_populates="user")
    created_at = created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), 
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
    
class Hotel(Base):
    __tablename__ = "hotels"
    id= Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable = False)
    description= Column(String, nullable = False)
    location = Column(String, nullable = False)
    bookings = relationship("Booking", back_populates="hotel")
    created_at = created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), 
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
    
class Booking(Base):
    __tablename__ = "booking"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)

    hotel_id = Column(UUID(as_uuid=True), ForeignKey("hotels.id"),nullable=False)
    start_time= Column(DateTime, nullable = False)
    end_time= Column(DateTime, nullable = False)
    user = relationship("User", back_populates="bookings")
    hotel = relationship("Hotel", back_populates="bookings")
    created_at = created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), 
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
    
class Events(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), 
                     default=lambda: datetime.now(timezone.utc),
                     onupdate=lambda: datetime.now(timezone.utc))
    start_time = Column(DateTime, nullable= False)
    end_time = Column(DateTime, nullable= False)
    description= Column(String, nullable= False)
    tags  =  Column(ARRAY(String),nullable=True)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    user = relationship("User", back_populates="events")