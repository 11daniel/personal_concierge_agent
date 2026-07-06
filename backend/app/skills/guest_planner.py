from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.user import Household
from app.models.guest_list import GuestEvent, Guest
from app.skills.base_skill import BaseSkill
from app.security import encrypt_value, decrypt_value

class GuestPlannerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "guest_planner"

    @property
    def description(self) -> str:
        return "Manages events, track invite lists, and RSVPs."

    def get_system_instructions(self) -> str:
        return """
Skill: guest_planner
Actions:
  - create_event:
      description: Create a new party or event.
      parameters:
        event_name: Name of the event (string, required, e.g. 'Birthday Bash')
        event_date: Date of the event (string, required, ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
  - add_guest:
      description: Add a guest to an event.
      parameters:
        event_name: Name of the event to add the guest to (string, required)
        guest_name: Name of the guest (string, required)
        guest_email: Email of the guest (string, optional)
        status: Invite status (string, optional, e.g. 'Pending', 'Attending', 'Declined')
  - update_guest_status:
      description: Update the RSVP status of a guest.
      parameters:
        event_name: Name of the event (string, required)
        guest_name: Name of the guest (string, required)
        status: The new status (string, required: 'Attending', 'Declined', or 'Pending')
  - list_events:
      description: Get all events and their guest lists.
      parameters: {}
"""

    def execute_action(self, db: Session, household_id: int, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        household = db.query(Household).filter(Household.id == household_id).first()
        if not household:
            return {"status": "error", "message": "Household not found"}
        salt = household.encryption_key_salt

        if action == "create_event":
            return self._create_event(db, household_id, salt, params)
        elif action == "add_guest":
            return self._add_guest(db, household_id, salt, params)
        elif action == "update_guest_status":
            return self._update_guest_status(db, household_id, salt, params)
        elif action == "list_events":
            return self._list_events(db, household_id, salt)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def _create_event(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        event_name = params.get("event_name")
        event_date_str = params.get("event_date")

        if not event_name or not event_date_str:
            return {"status": "error", "message": "Missing required fields (event_name, event_date)"}

        try:
            # Handle standard ISO formats
            if "T" in event_date_str:
                event_date = datetime.fromisoformat(event_date_str)
            else:
                event_date = datetime.strptime(event_date_str.split(" ")[0], "%Y-%m-%d")
        except Exception:
            event_date = datetime.utcnow() + timedelta(days=7) # Default to 1 week from now if parsing fails

        # Check if event with same name already exists
        all_events = db.query(GuestEvent).filter(GuestEvent.household_id == household_id).all()
        for ev in all_events:
            dec_name = decrypt_value(ev.event_name_encrypted, salt)
            if dec_name.lower() == event_name.lower():
                return {
                    "status": "warning",
                    "message": f"Event '{event_name}' already exists.",
                    "event": {
                        "id": ev.id,
                        "event_name": dec_name,
                        "event_date": ev.event_date.isoformat()
                    }
                }

        ev = GuestEvent(
            household_id=household_id,
            event_name_encrypted=encrypt_value(event_name, salt),
            event_date=event_date
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        return {
            "status": "success",
            "message": f"Successfully created event '{event_name}' on {event_date.strftime('%Y-%m-%d')}.",
            "event": {
                "id": ev.id,
                "event_name": event_name,
                "event_date": ev.event_date.isoformat()
            }
        }

    def _add_guest(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        event_name = params.get("event_name")
        guest_name = params.get("guest_name")
        guest_email = params.get("guest_email", "")
        status = params.get("status", "Pending")

        if not event_name or not guest_name:
            return {"status": "error", "message": "Missing event_name or guest_name"}

        # Find the event
        all_events = db.query(GuestEvent).filter(GuestEvent.household_id == household_id).all()
        target_event = None
        for ev in all_events:
            dec_name = decrypt_value(ev.event_name_encrypted, salt)
            if dec_name.lower() == event_name.lower():
                target_event = ev
                break

        if not target_event:
            return {"status": "error", "message": f"Event '{event_name}' not found. Please create it first."}

        # Check if guest already added
        guests = db.query(Guest).filter(Guest.event_id == target_event.id).all()
        for g in guests:
            dec_gname = decrypt_value(g.name_encrypted, salt)
            if dec_gname.lower() == guest_name.lower():
                return {"status": "warning", "message": f"Guest '{guest_name}' is already on the invite list."}

        new_guest = Guest(
            event_id=target_event.id,
            name_encrypted=encrypt_value(guest_name, salt),
            email_encrypted=encrypt_value(guest_email, salt) if guest_email else None,
            status=status
        )
        db.add(new_guest)
        db.commit()
        db.refresh(new_guest)

        return {
            "status": "success",
            "message": f"Added {guest_name} to '{event_name}' (Status: {status}).",
            "guest": {
                "id": new_guest.id,
                "name": guest_name,
                "email": guest_email,
                "status": status
            }
        }

    def _update_guest_status(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        event_name = params.get("event_name")
        guest_name = params.get("guest_name")
        status = params.get("status")

        if not event_name or not guest_name or not status:
            return {"status": "error", "message": "Missing event_name, guest_name or status"}

        # Find event
        all_events = db.query(GuestEvent).filter(GuestEvent.household_id == household_id).all()
        target_event = None
        for ev in all_events:
            dec_name = decrypt_value(ev.event_name_encrypted, salt)
            if dec_name.lower() == event_name.lower():
                target_event = ev
                break

        if not target_event:
            return {"status": "error", "message": f"Event '{event_name}' not found."}

        # Find guest
        guests = db.query(Guest).filter(Guest.event_id == target_event.id).all()
        target_guest = None
        for g in guests:
            dec_gname = decrypt_value(g.name_encrypted, salt)
            if dec_gname.lower() == guest_name.lower():
                target_guest = g
                break

        if not target_guest:
            return {"status": "error", "message": f"Guest '{guest_name}' not found for event '{event_name}'."}

        old_status = target_guest.status
        target_guest.status = status
        db.commit()

        return {
            "status": "success",
            "message": f"Updated RSVP for {guest_name} from {old_status} to {status}."
        }

    def _list_events(self, db: Session, household_id: int, salt: str) -> Dict[str, Any]:
        events = db.query(GuestEvent).filter(GuestEvent.household_id == household_id).all()
        resultList = []
        for ev in events:
            guests = db.query(Guest).filter(Guest.event_id == ev.id).all()
            guest_list = []
            for g in guests:
                guest_list.append({
                    "id": g.id,
                    "name": decrypt_value(g.name_encrypted, salt),
                    "email": decrypt_value(g.email_encrypted, salt) if g.email_encrypted else None,
                    "status": g.status
                })
            resultList.append({
                "id": ev.id,
                "event_name": decrypt_value(ev.event_name_encrypted, salt),
                "event_date": ev.event_date.isoformat(),
                "guests": guest_list
            })

        return {
            "status": "success",
            "events": resultList
        }
