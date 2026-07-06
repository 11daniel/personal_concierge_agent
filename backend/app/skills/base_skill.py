from abc import ABC, abstractmethod
from typing import Dict, Any
from sqlalchemy.orm import Session

class BaseSkill(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier of the skill (e.g. 'medication_tracker')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A user-friendly description of what this skill does."""
        pass

    @abstractmethod
    def get_system_instructions(self) -> str:
        """
        Instructions explaining what actions this skill supports and what parameters
        are required, which will be injected into the LLM orchestration prompt.
        """
        pass

    @abstractmethod
    def execute_action(self, db: Session, household_id: int, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a structured action on behalf of the household."""
        pass
