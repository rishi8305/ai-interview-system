from .auth import auth_bp
from .candidate import candidate_bp
from .interview import interview_bp
from .admin import admin_bp

__all__ = ["auth_bp", "candidate_bp", "interview_bp", "admin_bp"]
