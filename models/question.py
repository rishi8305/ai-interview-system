from datetime import datetime
import mongoengine as me
from . import BaseDocument


class Question(BaseDocument):
    """Question repository model in MongoDB."""

    meta = {"collection": "questions", "strict": False}

    id = me.SequenceField(primary_key=True)
    category = me.StringField(required=True, max_length=50)  # 'Technical', 'HR', 'Aptitude'
    topic = me.StringField(max_length=50)  # e.g., 'Python', 'Java', etc.
    difficulty = me.StringField(required=True, max_length=20, default="Medium")  # 'Easy', 'Medium', 'Hard'
    question_text = me.StringField(required=True)
    reference_answer = me.StringField()
    keywords = me.StringField()  # Comma-separated keywords
    is_generated = me.BooleanField(default=False)
    created_at = me.DateTimeField(default=datetime.utcnow)

    @property
    def responses(self):
        from .interview import Response
        return Response.query.filter_by(question_id=self.id)

    def to_dict(self):
        """Serialize question object."""
        return {
            "id": self.id,
            "category": self.category,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "question_text": self.question_text,
            "reference_answer": self.reference_answer,
            "keywords": [k.strip() for k in self.keywords.split(",")] if self.keywords else [],
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

    def __repr__(self):
        return f"<Question {self.id}: [{self.category} / {self.topic}] {self.question_text[:30]}...>"
