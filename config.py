import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Ensure instance directory exists
(BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "ai-interview-system-super-secret-key-2026")

    # MongoDB Configuration
    DATABASE_TYPE = os.getenv("DATABASE_TYPE", "mongodb").lower()
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/ai_interview_db")
    MONGODB_DB = os.getenv("MONGODB_DB", "ai_interview_db")

    # Legacy SQLite database URI (kept for fallback / test)
    raw_db_url = os.getenv("DATABASE_URL", "")
    if not raw_db_url or "instance/interview_system.db" in raw_db_url:
        db_path = (BASE_DIR / "instance" / "interview_system.db").as_posix()
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    else:
        SQLALCHEMY_DATABASE_URI = raw_db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # AI Configuration
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()  # 'gemini' or 'openai'
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Evaluation Mode: 'ai', 'rule_based', or 'auto'
    # 'auto' uses real AI if a valid API key exists, otherwise falls back to labeled rule-based evaluator
    EVALUATION_MODE = os.getenv("EVALUATION_MODE", "auto")

    # Application details
    APP_NAME = "AI Interview System"
    APP_VERSION = "1.0.0"

    # Email / SMTP Configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "").strip()
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "").strip()
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@aiinterview.com").strip()


class TestConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    EVALUATION_MODE = "rule_based"
    MAIL_SERVER = ""
    MAIL_USERNAME = ""
