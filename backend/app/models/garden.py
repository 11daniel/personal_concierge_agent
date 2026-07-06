from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

class GardenTask(Base):
    __tablename__ = "garden_tasks"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    plant_name_encrypted = Column(String, nullable=False)
    task_type_encrypted = Column(String, nullable=False) # e.g. "Water", "Harvest", "Prune", "Plant"
    due_date = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)

    household = relationship("Household", back_populates="garden_tasks")
