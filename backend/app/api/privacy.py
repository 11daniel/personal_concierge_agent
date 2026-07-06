from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any

from app.database import get_db
from app.models.user import User, Household
from app.models.medication import Medication, MedicationLog
from app.models.guest_list import GuestEvent, Guest
from app.models.garden import GardenTask
from app.models.session import ChatSession, ChatMessage
from app.models.audit import AuditLog
from app.schemas.privacy import AuditLogResponse, TransparencyResponse, HouseholdDataExport
from app.api.auth import get_current_user
from app.security import decrypt_value

router = APIRouter(prefix="/privacy", tags=["Privacy & Compliance"])

@router.get("/transparency", response_model=TransparencyResponse)
def get_transparency_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Provides transparency regarding what data is stored and which categories are active."""
    household_id = current_user.household_id
    
    # Simple count of records
    medications_count = db.query(Medication).filter(Medication.household_id == household_id).count()
    guests_count = db.query(Guest).join(GuestEvent).filter(GuestEvent.household_id == household_id).count()
    garden_tasks_count = db.query(GardenTask).filter(GardenTask.household_id == household_id).count()
    sessions_count = db.query(ChatSession).filter(ChatSession.household_id == household_id).count()
    
    active_skills = []
    if medications_count > 0:
        active_skills.append("Medication Tracker")
    if guests_count > 0:
        active_skills.append("Guest List Planner")
    if garden_tasks_count > 0:
        active_skills.append("Garden Planner")
        
    return {
        "household_info": {
            "id": household_id,
            "name": current_user.household.name,
            "created_users": [u.username for u in current_user.household.users]
        },
        "active_skills": active_skills,
        "medications_count": medications_count,
        "guests_count": guests_count,
        "garden_tasks_count": garden_tasks_count,
        "data_points": {
            "conversations": sessions_count,
            "medication_records": medications_count,
            "invitees": guests_count,
            "garden_schedules": garden_tasks_count
        }
    }

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_privacy_audits(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve security access audits for sensitive data reads/writes."""
    # List audits related to the household's users
    user_ids = [u.id for u in current_user.household.users]
    audits = db.query(AuditLog).filter(
        AuditLog.user_id.in_(user_ids)
    ).order_by(AuditLog.timestamp.desc()).all()
    return audits

@router.get("/export", response_model=HouseholdDataExport)
def export_household_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Exports all household data in an unencrypted plain-JSON format for data portability."""
    household_id = current_user.household_id
    salt = current_user.household.encryption_key_salt
    
    # 1. Audit log the export action
    audit = AuditLog(
        user_id=current_user.id,
        action="EXPORT_FULL_DATA",
        target_table="all"
    )
    db.add(audit)
    db.commit()

    # 2. Extract medications
    medications = db.query(Medication).filter(Medication.household_id == household_id).all()
    exported_meds = []
    for m in medications:
        logs = db.query(MedicationLog).filter(MedicationLog.medication_id == m.id).all()
        exported_meds.append({
            "name": decrypt_value(m.name_encrypted, salt),
            "dosage": decrypt_value(m.dosage_encrypted, salt),
            "schedule": decrypt_value(m.schedule_encrypted, salt),
            "active": m.active,
            "logs": [{
                "taken_at": l.taken_at.isoformat(),
                "notes": decrypt_value(l.notes_encrypted, salt) if l.notes_encrypted else ""
            } for l in logs]
        })

    # 3. Extract guests
    events = db.query(GuestEvent).filter(GuestEvent.household_id == household_id).all()
    exported_events = []
    for ev in events:
        guests = db.query(Guest).filter(Guest.event_id == ev.id).all()
        exported_events.append({
            "event_name": decrypt_value(ev.event_name_encrypted, salt),
            "event_date": ev.event_date.isoformat(),
            "guests": [{
                "name": decrypt_value(g.name_encrypted, salt),
                "email": decrypt_value(g.email_encrypted, salt) if g.email_encrypted else "",
                "status": g.status
            } for g in guests]
        })

    # 4. Extract garden tasks
    garden_tasks = db.query(GardenTask).filter(GardenTask.household_id == household_id).all()
    exported_garden = [{
        "plant_name": decrypt_value(t.plant_name_encrypted, salt),
        "task_type": decrypt_value(t.task_type_encrypted, salt),
        "due_date": t.due_date.isoformat(),
        "completed": t.completed
    } for t in garden_tasks]

    # 5. Extract chat history
    sessions = db.query(ChatSession).filter(ChatSession.household_id == household_id).all()
    exported_sessions = []
    for s in sessions:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).all()
        exported_sessions.append({
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "messages": [{
                "sender": m.sender,
                "text": decrypt_value(m.text_encrypted, salt),
                "created_at": m.created_at.isoformat()
            } for m in messages]
        })

    # 6. Extract audits
    user_ids = [u.id for u in current_user.household.users]
    audits_list = db.query(AuditLog).filter(AuditLog.user_id.in_(user_ids)).all()
    exported_audits = [{
        "action": a.action,
        "target_table": a.target_table,
        "timestamp": a.timestamp.isoformat()
    } for a in audits_list]

    return {
        "household_name": current_user.household.name,
        "export_timestamp": datetime.utcnow(),
        "medications": exported_meds,
        "guest_events": exported_events,
        "garden_tasks": exported_garden,
        "chat_sessions": exported_sessions,
        "audit_logs": exported_audits
    }

@router.delete("/purge", status_code=status.HTTP_200_OK)
def purge_household_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Deletes all data associated with this household permanently (Right to be Forgotten)."""
    household = db.query(Household).filter(Household.id == current_user.household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    # Perform cascading deletion of household (all related rows will be deleted by SQLAlchemy cascade)
    db.delete(household)
    db.commit()
    
    return {"status": "success", "message": "All household data, conversations, and accounts have been permanently purged."}
