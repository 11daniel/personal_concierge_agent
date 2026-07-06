import os
from pathlib import Path
from dotenv import load_dotenv

# Identify project root directory (parent of backend/)
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Load local environment variables from project root
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/personal_concierge.db")

# Security configurations
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day for easy MVP testing

# Static Master Key for field encryption salt/key derivation if user key is not available
# In production, this must be derived from the user's login password.
APP_ENCRYPTION_SALT = os.getenv("APP_ENCRYPTION_SALT", "concierge-salt-value-for-deriving-keys")

# LLM Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "false").lower() == "true" or not GEMINI_API_KEY
