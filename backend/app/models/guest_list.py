from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

class GuestEvent(Base):
    __tablename__ = "guest_events"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    event_name_encrypted = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False)

    household = relationship("Household", back_populates="guest_events")
    guests = relationship("Guest", back_populates="event", cascade="all, delete-orphan")

class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("guest_events.id"), nullable=False)
    name_encrypted = Column(String, nullable=False)
    email_encrypted = Column(String, nullable=True)
    status = Column(String, default="Pending", nullable=False) # Pending, Attending, Declined

    event = relationship("GuestEvent", back_populates="guests")
