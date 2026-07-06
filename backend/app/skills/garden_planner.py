from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.user import Household
from app.models.garden import GardenTask
from app.skills.base_skill import BaseSkill
from app.security import encrypt_value, decrypt_value

class GardenPlannerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "garden_planner"

    @property
    def description(self) -> str:
        return "Manages household and garden plant watering, pruning, and harvesting schedules."

    def get_system_instructions(self) -> str:
        return """
Skill: garden_planner
Actions:
  - add_task:
      description: Add a task for a plant (watering, planting, fertilizing, harvesting).
      parameters:
        plant_name: Name of the plant or garden area (string, required, e.g. 'Tomatoes' or 'Front Yard')
        task_type: Type of garden work (string, required, e.g. 'Water', 'Fertilize', 'Prune', 'Harvest', 'Plant')
        due_date: Scheduled date (string, required, ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
  - complete_task:
      description: Mark a garden task as completed.
      parameters:
        plant_name: Name of the plant (string, required)
        task_type: The task type that was completed (string, required, e.g. 'Water')
  - list_tasks:
      description: Retrieve the schedule of garden tasks.
      parameters: {}
"""

    def execute_action(self, db: Session, household_id: int, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        household = db.query(Household).filter(Household.id == household_id).first()
        if not household:
            return {"status": "error", "message": "Household not found"}
        salt = household.encryption_key_salt

        if action == "add_task":
            return self._add_task(db, household_id, salt, params)
        elif action == "complete_task":
            return self._complete_task(db, household_id, salt, params)
        elif action == "list_tasks":
            return self._list_tasks(db, household_id, salt)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def _add_task(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        plant_name = params.get("plant_name")
        task_type = params.get("task_type")
        due_date_str = params.get("due_date")

        if not plant_name or not task_type or not due_date_str:
            return {"status": "error", "message": "Missing required fields (plant_name, task_type, due_date)"}

        try:
            if "T" in due_date_str:
                due_date = datetime.fromisoformat(due_date_str)
            else:
                due_date = datetime.strptime(due_date_str.split(" ")[0], "%Y-%m-%d")
        except Exception:
            due_date = datetime.utcnow() # Default to today if parsing fails

        # Check for active duplicate task
        existing = db.query(GardenTask).filter(
            GardenTask.household_id == household_id,
            GardenTask.completed == False
        ).all()
        for t in existing:
            dec_p = decrypt_value(t.plant_name_encrypted, salt)
            dec_type = decrypt_value(t.task_type_encrypted, salt)
            if dec_p.lower() == plant_name.lower() and dec_type.lower() == task_type.lower():
                return {
                    "status": "warning",
                    "message": f"An uncompleted task for '{plant_name}' to '{task_type}' already exists due on {t.due_date.strftime('%Y-%m-%d')}."
                }

        task = GardenTask(
            household_id=household_id,
            plant_name_encrypted=encrypt_value(plant_name, salt),
            task_type_encrypted=encrypt_value(task_type, salt),
            due_date=due_date,
            completed=False
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return {
            "status": "success",
            "message": f"Scheduled task: {task_type} '{plant_name}' for {due_date.strftime('%Y-%m-%d')}.",
            "task": {
                "id": task.id,
                "plant_name": plant_name,
                "task_type": task_type,
                "due_date": task.due_date.isoformat(),
                "completed": task.completed
            }
        }

    def _complete_task(self, db: Session, household_id: int, salt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        plant_name = params.get("plant_name")
        task_type = params.get("task_type")

        if not plant_name or not task_type:
            return {"status": "error", "message": "Missing plant_name or task_type"}

        # Find active task
        active_tasks = db.query(GardenTask).filter(
            GardenTask.household_id == household_id,
            GardenTask.completed == False
        ).all()
        target_task = None
        for t in active_tasks:
            dec_p = decrypt_value(t.plant_name_encrypted, salt)
            dec_type = decrypt_value(t.task_type_encrypted, salt)
            if dec_p.lower() == plant_name.lower() and dec_type.lower() == task_type.lower():
                target_task = t
                break

        if not target_task:
            return {"status": "error", "message": f"No active task found to '{task_type}' '{plant_name}'."}

        target_task.completed = True
        db.commit()

        return {
            "status": "success",
            "message": f"Completed task: {task_type} '{plant_name}'."
        }

    def _list_tasks(self, db: Session, household_id: int, salt: str) -> Dict[str, Any]:
        tasks = db.query(GardenTask).filter(GardenTask.household_id == household_id).all()
        resultList = []
        for t in tasks:
            resultList.append({
                "id": t.id,
                "plant_name": decrypt_value(t.plant_name_encrypted, salt),
                "task_type": decrypt_value(t.task_type_encrypted, salt),
                "due_date": t.due_date.isoformat(),
                "completed": t.completed
            })

        return {
            "status": "success",
            "tasks": resultList
        }
