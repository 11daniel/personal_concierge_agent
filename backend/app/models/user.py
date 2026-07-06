import secrets
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # A unique salt generated upon creation, used to derive the field-level encryption key
    encryption_key_salt = Column(String, nullable=False, default=lambda: secrets.token_hex(16))

    users = relationship("User", back_populates="household", cascade="all, delete-orphan")
    sessions = relationship("ChatSession", back_populates="household", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="household", cascade="all, delete-orphan")
    guest_events = relationship("GuestEvent", back_populates="household", cascade="all, delete-orphan")
    garden_tasks = relationship("GardenTask", back_populates="household", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    household = relationship("Household", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
