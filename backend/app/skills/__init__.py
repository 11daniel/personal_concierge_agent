from app.skills.base_skill import BaseSkill
from app.skills.med_tracker import MedTrackerSkill
from app.skills.guest_planner import GuestPlannerSkill
from app.skills.garden_planner import GardenPlannerSkill

# Global dictionary of initialized skills
AVAILABLE_SKILLS = {
    "medication_tracker": MedTrackerSkill(),
    "guest_planner": GuestPlannerSkill(),
    "garden_planner": GardenPlannerSkill(),
}

__all__ = [
    "BaseSkill",
    "AVAILABLE_SKILLS",
    "MedTrackerSkill",
    "GuestPlannerSkill",
    "GardenPlannerSkill",
]
