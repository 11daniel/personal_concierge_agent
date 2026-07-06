from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    name_encrypted = Column(String, nullable=False)
    dosage_encrypted = Column(String, nullable=False)
    schedule_encrypted = Column(String, nullable=False) # e.g. "every 8 hours", "once daily"
    active = Column(Boolean, default=True, nullable=False)

    household = relationship("Household", back_populates="medications")
    logs = relationship("MedicationLog", back_populates="medication", cascade="all, delete-orphan")

class MedicationLog(Base):
    __tablename__ = "medication_logs"

    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    taken_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes_encrypted = Column(String, nullable=True)

    medication = relationship("Medication", back_populates="logs")
