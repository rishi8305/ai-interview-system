from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import mongoengine as me
from . import BaseDocument


class User(UserMixin, BaseDocument):
    """User model representing candidates and administrators in MongoDB."""

    meta = {"collection": "users", "strict": False}

    id = me.SequenceField(primary_key=True)
    name = me.StringField(required=True, max_length=120)
    email = me.StringField(required=True, unique=True, max_length=120)
    password_hash = me.StringField(required=True, max_length=255)
    role = me.StringField(default="candidate", max_length=20)  # 'candidate' or 'admin'
    created_at = me.DateTimeField(default=datetime.utcnow)

    def set_password(self, password: str):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify user password against hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """Check if user has administrative privileges."""
        return self.role == "admin"

    @property
    def interviews(self):
        """All interview sessions started by this user."""
        from .interview import Interview
        return Interview.query.filter_by(user_id=self.id).order_by("-started_at")

    @property
    def results(self):
        """All evaluation results for this user."""
        from .result import Result
        return Result.query.filter_by(user_id=self.id).order_by("-created_at")

    def to_dict(self):
        """Serialize user object."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
