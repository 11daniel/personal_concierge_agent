from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models.user import User
from app.models.medication import Medication
from app.models.guest_list import GuestEvent
from app.models.garden import GardenTask
from app.models.audit import AuditLog
from app.api.auth import get_current_user
from app.skills import AVAILABLE_SKILLS
from app.security import decrypt_value

router = APIRouter(prefix="/skills", tags=["Structured Logistics"])

# Helper to audit reads/writes
def log_audit(db: Session, user_id: int, action: str, table: str):
    audit = AuditLog(user_id=user_id, action=action, target_table=table)
    db.add(audit)
    db.commit()

# --- Medication Skill Endpoints ---

@router.get("/medications")
def list_medications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_audit(db, current_user.id, "READ_MEDICATIONS", "medications")
    skill = AVAILABLE_SKILLS["medication_tracker"]
    return skill.execute_action(db, current_user.household_id, "list_medications", {})

@router.post("/medications")
def add_medication(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_audit(db, current_user.id, "WRITE_MEDICATIONS", "medications")
    skill = AVAILABLE_SKILLS["medication_tracker"]
    return skill.execute_action(db, current_user.household_id, "add_medication", payload)

@router.post("/medications/{med_id}/take")
def log_medication_dose(med_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Find medication to get name
    med = db.query(Medication).filter(
        Medication.id == med_id, 
        Medication.household_id == current_user.household_id
    ).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    salt = current_user.household.encryption_key_salt
    med_name = decrypt_value(med.name_encrypted, salt)
    
    log_audit(db, current_user.id, "TAKE_MEDICATION", "medication_logs")
    skill = AVAILABLE_SKILLS["medication_tracker"]
    return skill.execute_action(db, current_user.household_id, "take_medication", {"name": med_name, "notes": "Logged via Dashboard"})

@router.post("/medications/{med_id}/deactivate")
def deactivate_medication(med_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    med = db.query(Medication).filter(
        Medication.id == med_id, 
        Medication.household_id == current_user.household_id
    ).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
        
    salt = current_user.household.encryption_key_salt
    med_name = decrypt_value(med.name_encrypted, salt)
    
    log_audit(db, current_user.id, "DEACTIVATE_MEDICATION", "medications")
    skill = AVAILABLE_SKILLS["medication_tracker"]
    return skill.execute_action(db, current_user.household_id, "deactivate_medication", {"name": med_name})


# --- Guest List Skill Endpoints ---

@router.get("/guests/events")
def list_events(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_audit(db, current_user.id, "READ_GUESTS", "guest_events")
    skill = AVAILABLE_SKILLS["guest_planner"]
    return skill.execute_action(db, current_user.household_id, "list_events", {})

@router.post("/guests/events")
def create_event(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_audit(db, current_user.id, "WRITE_GUEST_EVENT", "guest_events")
    skill = AVAILABLE_SKILLS["guest_planner"]
    return skill.execute_action(db, current_user.household_id, "create_event", payload)

@router.post("/guests/events/{event_id}/add-guest")
def add_guest(event_id: int, payload: Dict[str, Any], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Find event
    ev = db.query(GuestEvent).filter(
        GuestEvent.id == event_id,
        GuestEvent.household_id == current_user.household_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    salt = current_user.household.encryption_key_salt
    event_name = decrypt_value(ev.event_name_encrypted, salt)
    
    log_audit(db, current_user.id, "WRITE_GUEST", "guests")
    skill = AVAILABLE_SKILLS["guest_planner"]
    
    params = {
        "event_name": event_name,
        "guest_name": payload.get("guest_name"),
        "guest_email": payload.get("guest_email", ""),
        "status": payload.get("status", "Pending")
    }
    return skill.execute_action(db, current_user.household_id, "add_guest", params)

@router.post("/guests/events/{event_id}/update-guest")
def update_guest(event_id: int, payload: Dict[str, Any], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ev = db.query(GuestEvent).filter(
        GuestEvent.id == event_id,
        GuestEvent.household_id == current_user.household_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    salt = current_user.household.encryption_key_salt
    event_name = decrypt_value(ev.event_name_encrypted, salt)
    
    log_audit(db, current_user.id, "UPDATE_GUEST_STATUS", "guests")
    skill = AVAILABLE_SKILLS["guest_planner"]
    
    params = {
        "event_name": event_name,
        "guest_name": payload.get("guest_name"),
        "status": payload.get("status")
    }
    return skill.execute_action(db, current_user.household_id, "update_guest_status", params)


# --- Garden Skill Endpoints ---

@router.get("/garden")
def list_garden_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_audit(db, current_user.id, "READ_GARDEN", "garden_tasks")
    skill = AVAILABLE_SKILLS["garden_planner"]
    return skill.execute_action(db, current_user.household_id, "list_tasks", {})

@router.post("/garden")
def add_garden_task(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_audit(db, current_user.id, "WRITE_GARDEN", "garden_tasks")
    skill = AVAILABLE_SKILLS["garden_planner"]
    return skill.execute_action(db, current_user.household_id, "add_task", payload)

@router.post("/garden/{task_id}/complete")
def complete_garden_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(GardenTask).filter(
        GardenTask.id == task_id,
        GardenTask.household_id == current_user.household_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    salt = current_user.household.encryption_key_salt
    plant_name = decrypt_value(task.plant_name_encrypted, salt)
    task_type = decrypt_value(task.task_type_encrypted, salt)
    
    log_audit(db, current_user.id, "COMPLETE_GARDEN_TASK", "garden_tasks")
    skill = AVAILABLE_SKILLS["garden_planner"]
    
    return skill.execute_action(db, current_user.household_id, "complete_task", {
        "plant_name": plant_name,
        "task_type": task_type
    })
