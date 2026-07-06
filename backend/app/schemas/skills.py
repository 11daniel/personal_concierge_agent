from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

# --- Guest List Skill Schemas ---
class GuestBase(BaseModel):
    name: str
    email: Optional[str] = None
    status: str = "Pending"  # Pending, Attending, Declined

class GuestCreate(GuestBase):
    pass

class GuestResponse(GuestBase):
    id: int
    event_id: int

    model_config = ConfigDict(from_attributes=True)

class GuestEventBase(BaseModel):
    event_name: str
    event_date: datetime

class GuestEventCreate(GuestEventBase):
    pass

class GuestEventResponse(GuestEventBase):
    id: int
    household_id: int
    guests: List[GuestResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- Medication Tracker Skill Schemas ---
class MedicationLogBase(BaseModel):
    notes: Optional[str] = None

class MedicationLogCreate(MedicationLogBase):
    taken_at: Optional[datetime] = None

class MedicationLogResponse(BaseModel):
    id: int
    medication_id: int
    taken_at: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class MedicationBase(BaseModel):
    name: str
    dosage: str
    schedule: str  # e.g., "every 8 hours", "once daily"
    active: bool = True

class MedicationCreate(MedicationBase):
    pass

class MedicationResponse(MedicationBase):
    id: int
    household_id: int
    logs: List[MedicationLogResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- Garden Planner Skill Schemas ---
class GardenTaskBase(BaseModel):
    plant_name: str
    task_type: str  # Water, Prune, Plant, Harvest, Fertilize, etc.
    due_date: datetime
    completed: bool = False

class GardenTaskCreate(GardenTaskBase):
    pass

class GardenTaskResponse(GardenTaskBase):
    id: int
    household_id: int

    model_config = ConfigDict(from_attributes=True)
