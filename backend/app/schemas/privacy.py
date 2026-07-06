from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Dict, Any

class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    target_table: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class TransparencyResponse(BaseModel):
    household_info: Dict[str, Any]
    active_skills: List[str]
    medications_count: int
    guests_count: int
    garden_tasks_count: int
    data_points: Dict[str, Any]  # A summary count of data items stored

class HouseholdDataExport(BaseModel):
    household_name: str
    export_timestamp: datetime
    medications: List[Dict[str, Any]]
    guest_events: List[Dict[str, Any]]
    garden_tasks: List[Dict[str, Any]]
    chat_sessions: List[Dict[str, Any]]
    audit_logs: List[Dict[str, Any]]
