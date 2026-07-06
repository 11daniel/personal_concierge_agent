from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.skills import router as skills_router
from app.api.privacy import router as privacy_router

__all__ = ["auth_router", "chat_router", "skills_router", "privacy_router"]
