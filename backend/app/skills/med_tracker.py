from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.user import Household
from app.models.medication import Medication, MedicationLog
from app.skills.base_skill import BaseSkill
from app.security import encrypt_value, decrypt_value

class MedTrackerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "medication_tracker"

    @property
    def description(self) -> str:
        return "Tracks medications, schedules, dosages, and compliance logs."

    def get_system_instructions(self) -> str:
        return """
Skill: medication_tracker
Actions:
  - add_medication:
      description: Record a new medication schedule.
      parameters:
        name: Name of the medication (string, required)
        dosage: Dosage amount (string, required, e.g. '500mg' or '1 pill')
        schedule: How often to take it (string, required, e.g. 'every 8 hours' or 'once daily')
  - take_medication:
      description: Log that a medication dose was just taken.
      parameters:
        name: Name of the medication taken (string, required)
        notes: Optional comments (string, optional, e.g. 'taken with food')
  - list_medications:
      description: Get all medications currently tracked for the household.
      parameters: {}
  - deactivate_medication:
      description: Deactivate medication tracking.
      parameters:
        name: Name of the medication to stop tracking (string, required)
"""

    def execute_action(self, db: Session, household_id: int, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Fetch the household to get the salt for encryption/decryption
        household = db.query(Household).filter(Household.id == household_id).first()
        if not household:
            return {"status": "error", "message": "Household not found"}
        salt = household.encryption_key_salt

        if action == "add_medication":
            return self._add_medication(db, household_id, salt, params)
        elif action == "take_medication":
            return self._take_medication(db, household_id, salt, params)
        elif action == "list_medications":
            return self._list_medications(db, household_id, salt)
        elif action == "deactivate_medication":
            return self._deactivate_medication(db, household_id, salt, params)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def _add_medication(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        dosage = params.get("dosage")
        schedule = params.get("schedule")

        if not name or not dosage or not schedule:
            return {"status": "error", "message": "Missing required fields (name, dosage, schedule)"}

        # Check if active medication with same name already exists
        all_meds = db.query(Medication).filter(Medication.household_id == household_id, Medication.active == True).all()
        for m in all_meds:
            dec_name = decrypt_value(m.name_encrypted, salt)
            if dec_name.lower() == name.lower():
                return {
                    "status": "warning",
                    "message": f"Medication '{name}' is already being tracked.",
                    "medication": {
                        "id": m.id,
                        "name": dec_name,
                        "dosage": decrypt_value(m.dosage_encrypted, salt),
                        "schedule": decrypt_value(m.schedule_encrypted, salt)
                    }
                }

        # Encrypt sensitive medical information before saving to DB
        med = Medication(
            household_id=household_id,
            name_encrypted=encrypt_value(name, salt),
            dosage_encrypted=encrypt_value(dosage, salt),
            schedule_encrypted=encrypt_value(schedule, salt),
            active=True
        )
        db.add(med)
        db.commit()
        db.refresh(med)

        return {
            "status": "success",
            "message": f"Now tracking medication: {name} ({dosage}, {schedule})",
            "medication": {
                "id": med.id,
                "name": name,
                "dosage": dosage,
                "schedule": schedule
            }
        }

    def _take_medication(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        notes = params.get("notes", "")

        if not name:
            return {"status": "error", "message": "Missing medication name"}

        # Find active medication by decrypted name matching
        all_meds = db.query(Medication).filter(Medication.household_id == household_id, Medication.active == True).all()
        target_med = None
        for m in all_meds:
            dec_name = decrypt_value(m.name_encrypted, salt)
            if dec_name.lower() == name.lower():
                target_med = m
                break

        if not target_med:
            return {"status": "error", "message": f"No active medication found named '{name}'"}

        log = MedicationLog(
            medication_id=target_med.id,
            taken_at=datetime.utcnow(),
            notes_encrypted=encrypt_value(notes, salt) if notes else None
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        return {
            "status": "success",
            "message": f"Logged dose of {name} taken at {log.taken_at.strftime('%Y-%m-%d %H:%M:%S')} UTC.",
            "log": {
                "id": log.id,
                "medication_name": name,
                "taken_at": log.taken_at.isoformat(),
                "notes": notes
            }
        }

    def _list_medications(self, db: Session, household_id: int, salt: str) -> Dict[str, Any]:
        meds = db.query(Medication).filter(Medication.household_id == household_id).all()
        resultList = []
        for m in meds:
            # Get last log
            last_log_record = db.query(MedicationLog).filter(MedicationLog.medication_id == m.id).order_by(MedicationLog.taken_at.desc()).first()
            last_taken = last_log_record.taken_at.isoformat() if last_log_record else None
            last_notes = decrypt_value(last_log_record.notes_encrypted, salt) if last_log_record and last_log_record.notes_encrypted else None

            resultList.append({
                "id": m.id,
                "name": decrypt_value(m.name_encrypted, salt),
                "dosage": decrypt_value(m.dosage_encrypted, salt),
                "schedule": decrypt_value(m.schedule_encrypted, salt),
                "active": m.active,
                "last_taken": last_taken,
                "last_taken_notes": last_notes
            })

        return {
            "status": "success",
            "medications": resultList
        }

    def _deactivate_medication(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not name:
            return {"status": "error", "message": "Missing medication name"}

        # Find medication to deactivate
        meds = db.query(Medication).filter(Medication.household_id == household_id, Medication.active == True).all()
        target_med = None
        for m in meds:
            dec_name = decrypt_value(m.name_encrypted, salt)
            if dec_name.lower() == name.lower():
                target_med = m
                break

        if not target_med:
            return {"status": "error", "message": f"No active medication found named '{name}'"}

        target_med.active = False
        db.commit()

        return {
            "status": "success",
            "message": f"Stopped tracking medication: {name}"
        }
