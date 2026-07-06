from sqlalchemy.orm import Session
from app.models.session import ChatMessage
from app.security import decrypt_value

class MemoryService:
    @staticmethod
    def get_formatted_history(db: Session, session_id: int, salt: str, limit: int = 10) -> str:
        """
        Retrieves the last N messages of a conversation session, decrypts them,
        and formats them into a clean string representation for LLM context.
        """
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).all()

        # Only get the last limit messages
        recent_messages = messages[-limit:] if len(messages) > limit else messages

        formatted_lines = []
        for msg in recent_messages:
            sender_label = "User" if msg.sender == "user" else "Assistant"
            # Decrypt conversation content at rest
            decrypted_text = decrypt_value(msg.text_encrypted, salt)
            formatted_lines.append(f"{sender_label}: {decrypted_text}")

        return "\n".join(formatted_lines)
