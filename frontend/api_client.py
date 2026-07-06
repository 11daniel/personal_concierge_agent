import requests
from typing import Dict, Any, List, Optional
import streamlit as st

class ConciergeApiClient:
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if "token" in st.session_state and st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
        return headers

    def _request(self, method: str, path: str, json_data: Any = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                headers=self._get_headers()
            )
            if response.status_code in [200, 201]:
                return response.json()
            else:
                # Handle error payload if available
                try:
                    error_detail = response.json().get("detail", "Request failed")
                except Exception:
                    error_detail = response.text
                return {"status": "error", "message": error_detail, "code": response.status_code}
        except Exception as e:
            return {"status": "error", "message": f"Connection error: {str(e)}", "code": 500}

    # --- Auth ---
    def register(self, username: str, password: str, household_name: str) -> Dict[str, Any]:
        return self._request("POST", "/auth/register", {
            "username": username,
            "password": password,
            "household_name": household_name
        })

    def login(self, username: str, password: str) -> Dict[str, Any]:
        return self._request("POST", "/auth/token", {
            "username": username,
            "password": password
        })

    # --- Chat ---
    def create_session(self) -> Dict[str, Any]:
        return self._request("POST", "/chat/sessions")

    def list_sessions(self) -> List[Dict[str, Any]]:
        res = self._request("GET", "/chat/sessions")
        if isinstance(res, list):
            return res
        return []

    def get_session_history(self, session_id: int) -> List[Dict[str, Any]]:
        res = self._request("GET", f"/chat/sessions/{session_id}/history")
        if isinstance(res, list):
            return res
        return []

    def send_message(self, session_id: int, text: str) -> Dict[str, Any]:
        return self._request("POST", f"/chat/sessions/{session_id}/message", {"text": text})

    # --- Medication Skill ---
    def list_medications(self) -> Dict[str, Any]:
        return self._request("GET", "/skills/medications")

    def add_medication(self, name: str, dosage: str, schedule: str) -> Dict[str, Any]:
        return self._request("POST", "/skills/medications", {
            "name": name,
            "dosage": dosage,
            "schedule": schedule
        })

    def take_medication(self, med_id: int) -> Dict[str, Any]:
        return self._request("POST", f"/skills/medications/{med_id}/take")

    def deactivate_medication(self, med_id: int) -> Dict[str, Any]:
        return self._request("POST", f"/skills/medications/{med_id}/deactivate")

    # --- Guest List Skill ---
    def list_events(self) -> Dict[str, Any]:
        return self._request("GET", "/skills/guests/events")

    def create_event(self, event_name: str, event_date: str) -> Dict[str, Any]:
        return self._request("POST", "/skills/guests/events", {
            "event_name": event_name,
            "event_date": event_date
        })

    def add_guest(self, event_id: int, guest_name: str, guest_email: str = "", status: str = "Pending") -> Dict[str, Any]:
        return self._request("POST", f"/skills/guests/events/{event_id}/add-guest", {
            "guest_name": guest_name,
            "guest_email": guest_email,
            "status": status
        })

    def update_guest_rsvp(self, event_id: int, guest_name: str, status: str) -> Dict[str, Any]:
        return self._request("POST", f"/skills/guests/events/{event_id}/update-guest", {
            "guest_name": guest_name,
            "status": status
        })

    # --- Garden Skill ---
    def list_garden_tasks(self) -> Dict[str, Any]:
        return self._request("GET", "/skills/garden")

    def add_garden_task(self, plant_name: str, task_type: str, due_date: str) -> Dict[str, Any]:
        return self._request("POST", "/skills/garden", {
            "plant_name": plant_name,
            "task_type": task_type,
            "due_date": due_date
        })

    def complete_garden_task(self, task_id: int) -> Dict[str, Any]:
        return self._request("POST", f"/skills/garden/{task_id}/complete")

    # --- Privacy & Compliance ---
    def get_transparency_summary(self) -> Dict[str, Any]:
        return self._request("GET", "/privacy/transparency")

    def get_audit_logs(self) -> List[Dict[str, Any]]:
        res = self._request("GET", "/privacy/audit-logs")
        if isinstance(res, list):
            return res
        return []

    def export_data(self) -> Dict[str, Any]:
        return self._request("GET", "/privacy/export")

    def purge_data(self) -> Dict[str, Any]:
        return self._request("DELETE", "/privacy/purge")
