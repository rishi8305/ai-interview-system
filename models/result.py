import json
from datetime import datetime
import mongoengine as me
from . import BaseDocument


class Result(BaseDocument):
    """Final aggregated interview result in MongoDB."""

    meta = {"collection": "results", "strict": False}

    id = me.SequenceField(primary_key=True)
    interview_id = me.IntField(required=True, unique=True)
    user_id = me.IntField(required=True)

    total_score = me.FloatField(default=0.0)
    percentage = me.FloatField(default=0.0)
    raw_score = me.FloatField(default=0.0)
    proctoring_penalty = me.FloatField(default=0.0)
    tab_switch_count = me.IntField(default=0)
    violations_count = me.IntField(default=0)
    integrity_score = me.FloatField(default=100.0)
    correctness_avg = me.FloatField(default=0.0)
    relevance_avg = me.FloatField(default=0.0)
    completeness_avg = me.FloatField(default=0.0)
    clarity_avg = me.FloatField(default=0.0)

    strengths_json = me.StringField(default="[]")
    weaknesses_json = me.StringField(default="[]")
    recommendations_json = me.StringField(default="[]")
    proctoring_summary_json = me.StringField(default="{}")
    created_at = me.DateTimeField(default=datetime.utcnow)

    @property
    def interview(self):
        from .interview import Interview
        return Interview.query.get(self.interview_id)

    @property
    def user(self):
        from .user import User
        return User.query.get(self.user_id)

    @property
    def strengths(self):
        try:
            return json.loads(self.strengths_json) if self.strengths_json else []
        except Exception:
            return []

    @strengths.setter
    def strengths(self, value):
        self.strengths_json = json.dumps(value if isinstance(value, list) else [])

    @property
    def weaknesses(self):
        try:
            return json.loads(self.weaknesses_json) if self.weaknesses_json else []
        except Exception:
            return []

    @weaknesses.setter
    def weaknesses(self, value):
        self.weaknesses_json = json.dumps(value if isinstance(value, list) else [])

    @property
    def recommendations(self):
        try:
            return json.loads(self.recommendations_json) if self.recommendations_json else []
        except Exception:
            return []

    @recommendations.setter
    def recommendations(self, value):
        self.recommendations_json = json.dumps(value if isinstance(value, list) else [])

    def to_dict(self):
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "user_id": self.user_id,
            "total_score": round(self.total_score, 1),
            "percentage": round(self.percentage, 1),
            "correctness_avg": round(self.correctness_avg, 1),
            "relevance_avg": round(self.relevance_avg, 1),
            "completeness_avg": round(self.completeness_avg, 1),
            "clarity_avg": round(self.clarity_avg, 1),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

    def __repr__(self):
        return f"<Result {self.id}: Interview {self.interview_id} - {self.percentage}%>"
