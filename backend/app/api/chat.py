from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app.models.user import User, Household
from app.models.session import ChatSession, ChatMessage
from app.models.audit import AuditLog
from app.schemas.chat import SessionResponse, ChatDetailResponse, MessageCreate, MessageResponse
from app.api.auth import get_current_user
from app.security import encrypt_value, decrypt_value
from app.services.llm_orchestrator import LlmOrchestrator
from app.services.memory_service import MemoryService
from app.skills import AVAILABLE_SKILLS

router = APIRouter(prefix="/chat", tags=["Conversations"])
orchestrator = LlmOrchestrator()

@router.post("/sessions", response_model=SessionResponse)
def create_session(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = ChatSession(
        household_id=current_user.household_id,
        title=f"Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = db.query(ChatSession).filter(
        ChatSession.household_id == current_user.household_id
    ).order_by(ChatSession.created_at.desc()).all()
    return sessions

@router.get("/sessions/{session_id}/history", response_model=List[MessageResponse])
def get_session_history(
    session_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.household_id == current_user.household_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    salt = current_user.household.encryption_key_salt
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    decrypted_messages = []
    for msg in messages:
        decrypted_messages.append({
            "id": msg.id,
            "sender": msg.sender,
            "text": decrypt_value(msg.text_encrypted, salt),
            "created_at": msg.created_at
        })
    return decrypted_messages

@router.post("/sessions/{session_id}/message", response_model=MessageResponse)
def send_message(
    session_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.household_id == current_user.household_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    salt = current_user.household.encryption_key_salt
    user_text = payload.text.strip()

    # 1. Save User Message Encrypted
    user_msg = ChatMessage(
        session_id=session_id,
        sender="user",
        text_encrypted=encrypt_value(user_text, salt)
    )
    db.add(user_msg)
    db.commit()

    # 2. Get history context
    history_context = MemoryService.get_formatted_history(db, session_id, salt)

    # 3. Call Orchestrator
    llm_output = orchestrator.parse_message(user_text, history_context)

    # 4. Trigger Skills if matched
    skill_name = llm_output.get("skill")
    action_name = llm_output.get("action")
    params = llm_output.get("parameters", {})
    assistant_response = llm_output.get("conversational_response", "I'm not sure how to help with that.")

    if skill_name and skill_name in AVAILABLE_SKILLS:
        skill = AVAILABLE_SKILLS[skill_name]
        try:
            # Audit log for sensitive skill execution
            audit = AuditLog(
                user_id=current_user.id,
                action=f"EXECUTE_{action_name.upper()}",
                target_table=skill_name
            )
            db.add(audit)
            
            # Execute skill
            execution_result = skill.execute_action(db, current_user.household_id, action_name, params)
            
            # Override response or add info if needed
            if execution_result.get("status") == "error":
                assistant_response = f"Sorry, I couldn't complete that action. Error: {execution_result.get('message')}"
            else:
                # If the execution returned structured listings, format them into the response text
                if "events" in execution_result:
                    events = execution_result["events"]
                    if events:
                        lines = ["Here are your planned events:"]
                        for e in events:
                            try:
                                dt = datetime.fromisoformat(e["event_date"]).strftime('%B %d, %Y')
                            except Exception:
                                dt = e["event_date"].split("T")[0]
                            lines.append(f"- **{e['event_name']}** on {dt}")
                            if e.get("guests"):
                                guests_str = ", ".join([f"{g['name']} ({g['status']})" for g in e["guests"]])
                                lines.append(f"  *Guests: {guests_str}*")
                        assistant_response = "\n".join(lines)
                    else:
                        assistant_response = "You don't have any planned events right now."
                elif "medications" in execution_result:
                    meds = execution_result["medications"]
                    if meds:
                        lines = ["Here are your tracked medications:"]
                        for m in meds:
                            status = "Active" if m["active"] else "Inactive"
                            last_log = f", last taken: {m['last_taken'].split('T')[0]}" if m.get("last_taken") else ""
                            lines.append(f"- **{m['name']}** ({m['dosage']}, {m['schedule']}) - *{status}*{last_log}")
                        assistant_response = "\n".join(lines)
                    else:
                        assistant_response = "No medications are currently being tracked."
                elif "tasks" in execution_result:
                    tasks = execution_result["tasks"]
                    if tasks:
                        lines = ["Here is your garden schedule:"]
                        for t in tasks:
                            status = "✅ Completed" if t["completed"] else "⏳ Pending"
                            try:
                                dt = datetime.fromisoformat(t["due_date"]).strftime('%B %d, %Y')
                            except Exception:
                                dt = t["due_date"].split("T")[0]
                            lines.append(f"- **{t['task_type']} {t['plant_name']}** (Due: {dt}) - *{status}*")
                        assistant_response = "\n".join(lines)
                    else:
                        assistant_response = "Your garden task schedule is empty."
                else:
                    # Fallback to standard message if present
                    skill_msg = execution_result.get("message")
                    if skill_msg:
                        assistant_response = skill_msg
        except Exception as e:
            assistant_response = f"An error occurred while executing the {skill_name} skill: {str(e)}"
            db.rollback()

    # 5. Update session title if default
    if session.title.startswith("Chat -"):
        # Auto summarize a title
        words = user_text.split()
        summary = " ".join(words[:4]) + "..." if len(words) > 4 else user_text
        session.title = summary
        db.commit()

    # 6. Save Assistant Message Encrypted
    assistant_msg = ChatMessage(
        session_id=session_id,
        sender="assistant",
        text_encrypted=encrypt_value(assistant_response, salt)
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # Return decrypted message response to user
    return {
        "id": assistant_msg.id,
        "sender": "assistant",
        "text": assistant_response,
        "created_at": assistant_msg.created_at
    }
