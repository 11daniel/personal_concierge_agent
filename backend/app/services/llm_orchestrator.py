import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
import google.generativeai as genai

from app.config import GEMINI_API_KEY, USE_MOCK_LLM
from app.skills import AVAILABLE_SKILLS

class LlmOrchestrator:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.use_mock = USE_MOCK_LLM or not self.api_key
        if not self.use_mock:
            try:
                genai.configure(api_key=self.api_key)
                # Use gemini-2.5-flash since 1.5-flash is no longer supported on this API key's endpoint
                self.model = genai.GenerativeModel("models/gemini-2.5-flash")
            except Exception as e:
                print(f"Error configuring Gemini, falling back to mock: {e}")
                self.use_mock = True

    def parse_message(self, user_message: str, history_context: str) -> Dict[str, Any]:
        """
        Parses a natural language user message, references conversational history,
        and determines if a structured skill action should be triggered.
        Returns a dictionary containing:
          - skill: Name of the target skill (or None)
          - action: Name of the action (or None)
          - parameters: Dict of parameters parsed
          - conversational_response: A pleasant textual response describing the action
        """
        if self.use_mock:
            return self._mock_parse(user_message, history_context)

        # Build prompt containing system instruction and available skills
        skills_instruction = "\n\n".join([
            f"--- Skill: {name} ---\n{skill.get_system_instructions()}"
            for name, skill in AVAILABLE_SKILLS.items()
        ])

        prompt = f"""
You are the AI brain of a Personal Concierge Agent.
Your job is to parse a natural language message from a user in a household and decide if it triggers one of the available skill actions.
You must return a JSON response with the following format:
{{
  "skill": "skill_name" or null,
  "action": "action_name" or null,
  "parameters": {{ ... }} or {{}},
  "conversational_response": "A direct, friendly confirmation of the action or a general response. If a skill action is matched, explain what you did. Be concise."
}}

If the user request is just general chat (e.g. "hello", "how are you"), set "skill" and "action" to null and provide a friendly conversational response.

--- Current Time Context ---
Today is: {datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")}

--- Conversation History Context ---
{history_context}

--- Available Skills ---
{skills_instruction}

User Message: "{user_message}"

Respond strictly with a JSON object. Ensure JSON keys and values match the requested schemas exactly.
"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text.strip())
            return data
        except Exception as e:
            print(f"Gemini API request failed ({e}), using mock fallback.")
            return self._mock_parse(user_message, history_context)

    def _mock_parse(self, msg: str, history: str) -> Dict[str, Any]:
        """Fallback regex parser in case Gemini API is unavailable or disabled."""
        msg_lower = msg.lower()
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Medication - Add
        # "I need to take 500mg of Tylenol every 8 hours" or "Track medication Tylenol, 500mg, every 8 hours"
        med_add_match = re.search(r'(?:track|add|need to take)\s+(?:medication\s+)?([\w\s]+?)[,\s]+(\d+\s*\w+)\s+(?:every|once|twice|daily)\s+([\w\s]+)', msg_lower)
        if med_add_match:
            name = med_add_match.group(1).strip().title()
            dosage = med_add_match.group(2).strip()
            schedule = "every " + med_add_match.group(3).strip()
            return {
                "skill": "medication_tracker",
                "action": "add_medication",
                "parameters": {"name": name, "dosage": dosage, "schedule": schedule},
                "conversational_response": f"Sure! I've added '{name}' ({dosage}, {schedule}) to your medication tracker."
            }

        # Simple medication add fallback: "Track Tylenol 500mg daily"
        med_simple_add = re.search(r'track\s+([\w\-]+)\s+(\d+\w+)\s+([\w\s]+)', msg_lower)
        if med_simple_add:
            name = med_simple_add.group(1).strip().title()
            dosage = med_simple_add.group(2).strip()
            schedule = med_simple_add.group(3).strip()
            return {
                "skill": "medication_tracker",
                "action": "add_medication",
                "parameters": {"name": name, "dosage": dosage, "schedule": schedule},
                "conversational_response": f"Added '{name}' ({dosage}, {schedule}) to your medications."
            }

        # 2. Medication - Take
        # "I took my Tylenol" or "log dose of Advil"
        med_take_match = re.search(r'(?:took my|logged|log dose of|took|taken)\s+([\w\s\-]+)', msg_lower)
        if med_take_match:
            name = med_take_match.group(1).replace("my", "").strip().title()
            return {
                "skill": "medication_tracker",
                "action": "take_medication",
                "parameters": {"name": name, "notes": "Logged via conversation"},
                "conversational_response": f"Dose of {name} logged successfully."
            }

        # 3. Garden - Add/Water
        # "Schedule watering Tomatoes for tomorrow" or "Water the Roses today"
        garden_add_match = re.search(r'(?:water|prune|harvest|fertilize|plant)\s+(?:the\s+)?([\w\s]+?)(?:\s+(today|tomorrow|yesterday|on\s+[\d\-]+))?$', msg_lower)
        if garden_add_match:
            plant = garden_add_match.group(1).strip().title()
            due_word = garden_add_match.group(2) or "today"
            due_date = datetime.now()
            if "tomorrow" in due_word:
                due_date += timedelta(days=1)
            due_date_str = due_date.strftime("%Y-%m-%d")

            action_type = "Water"
            for t in ["water", "prune", "harvest", "fertilize", "plant"]:
                if t in msg_lower:
                    action_type = t.title()
                    break

            return {
                "skill": "garden_planner",
                "action": "add_task",
                "parameters": {"plant_name": plant, "task_type": action_type, "due_date": due_date_str},
                "conversational_response": f"Scheduled a '{action_type}' task for your '{plant}' due on {due_date_str}."
            }

        # 4. Guest - Create Event
        # "Create event Birthday Party for 2026-08-15"
        event_match = re.search(r'(?:create|schedule)\s+(?:event|party|meeting)\s+([\w\s]+?)\s+on\s+([\d\-]+)', msg_lower)
        if event_match:
            event_name = event_match.group(1).strip().title()
            event_date = event_match.group(2).strip()
            return {
                "skill": "guest_planner",
                "action": "create_event",
                "parameters": {"event_name": event_name, "event_date": event_date},
                "conversational_response": f"I've created the event '{event_name}' scheduled for {event_date}."
            }

        # 5. Guest - Add Guest
        # "Add John to Birthday Party" or "Invite Sarah to the Wedding"
        guest_add_match = re.search(r'(?:invite|add)\s+([\w\s]+?)\s+(?:to|for)\s+([\w\s]+)', msg_lower)
        if guest_add_match:
            guest_name = guest_add_match.group(1).strip().title()
            event_name = guest_add_match.group(2).replace("the", "").strip().title()
            return {
                "skill": "guest_planner",
                "action": "add_guest",
                "parameters": {"event_name": event_name, "guest_name": guest_name, "status": "Pending"},
                "conversational_response": f"I've added {guest_name} to the guest list for '{event_name}'."
            }

        # 6. Guest - RSVP Status
        # "Mark John as Attending for Birthday Party"
        guest_rsvp_match = re.search(r'(?:mark|set)\s+([\w\s]+?)\s+as\s+(attending|declined|pending)\s+(?:for|on)\s+([\w\s]+)', msg_lower)
        if guest_rsvp_match:
            guest_name = guest_rsvp_match.group(1).strip().title()
            status = guest_rsvp_match.group(2).strip().title()
            event_name = guest_rsvp_match.group(3).strip().title()
            return {
                "skill": "guest_planner",
                "action": "update_guest_status",
                "parameters": {"event_name": event_name, "guest_name": guest_name, "status": status},
                "conversational_response": f"RSVP updated: {guest_name} is now '{status}' for '{event_name}'."
            }

        # General conversation response
        return {
            "skill": None,
            "action": None,
            "parameters": {},
            "conversational_response": (
                "Hello! I am your Personal Concierge. I can help you track medications, guest lists, and garden schedules.\n\n"
                "Try saying things like:\n"
                "- *'Track medication Lipitor, 10mg, once daily'*\n"
                "- *'I took my Lipitor'*\n"
                "- *'Create event Summer BBQ on 2026-07-20'*\n"
                "- *'Invite Sarah to Summer BBQ'*\n"
                "- *'Water the Tomatoes tomorrow'*"
            )
        }
