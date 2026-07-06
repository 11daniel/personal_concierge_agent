from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api import auth_router, chat_router, skills_router, privacy_router
import app.models  # Imports all models to ensure they are registered

# Automatically create database tables for SQLite MVP
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Personal Concierge API Backend",
    description="Secure, field-encrypted API backing the Streamlit Personal Concierge.",
    version="1.0.0",
)

# Setup CORS for Streamlit frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes under /api
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(privacy_router, prefix="/api")

@app.get("/")
def home():
    return {
        "status": "healthy",
        "service": "Personal Concierge Agent Backend",
        "encryption": "AES-256-GCM field-level active",
    }
