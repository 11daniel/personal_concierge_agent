import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set database env to local SQLite file for testing to share state across connection pool
import os
os.environ["DATABASE_URL"] = "sqlite:///test_concierge.db"
os.environ["USE_MOCK_LLM"] = "True" # Force mock LLM parsing for deterministic tests

from app.main import app
from app.database import Base, get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Retrieve engine from main
    from app.database import engine, SessionLocal
    import app.models  # Ensure models are registered on Base
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Truncate tables between tests instead of unlinking SQLite file
    db = SessionLocal()
    try:
        # Delete in reverse order to respect foreign key constraints
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def test_register_and_login():
    # 1. Register
    reg_response = client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpassword",
        "household_name": "Test Household"
    })
    assert reg_response.status_code == 201
    data = reg_response.json()
    assert data["username"] == "testuser"
    assert "household_id" in data

    # 2. Login
    login_response = client.post("/api/auth/token", json={
        "username": "testuser",
        "password": "testpassword"
    })
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def test_secured_chat_flow():
    # Register and login to get JWT
    client.post("/api/auth/register", json={
        "username": "chatuser",
        "password": "chatpassword",
        "household_name": "Chat Household"
    })
    login_response = client.post("/api/auth/token", json={
        "username": "chatuser",
        "password": "chatpassword"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    sess_response = client.post("/api/chat/sessions", headers=headers)
    assert sess_response.status_code == 200
    session_id = sess_response.json()["id"]

    # Send message to add medication
    msg_response = client.post(
        f"/api/chat/sessions/{session_id}/message", 
        json={"text": "Track medication Lipitor, 10mg once daily"},
        headers=headers
    )
    assert msg_response.status_code == 200
    assert "Lipitor" in msg_response.json()["text"]

    # Retrieve medications list directly and verify encryption decrypted correctly
    meds_response = client.get("/api/skills/medications", headers=headers)
    assert meds_response.status_code == 200
    meds = meds_response.json()["medications"]
    assert len(meds) == 1
    assert meds[0]["name"] == "Lipitor"
    assert meds[0]["dosage"] == "10mg"
    assert meds[0]["schedule"] == "every daily"
    assert meds[0]["active"] is True
