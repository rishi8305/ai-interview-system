import json
from datetime import datetime
import mongoengine as me
from . import BaseDocument


class Interview(BaseDocument):
    """Interview session model in MongoDB."""

    meta = {"collection": "interviews", "strict": False}

    id = me.SequenceField(primary_key=True)
    user_id = me.IntField(required=True)
    category = me.StringField(required=True, max_length=50)  # 'Technical', 'HR', 'Aptitude'
    topic = me.StringField(max_length=50)  # e.g., 'Python', 'Java', etc.
    difficulty = me.StringField(required=True, max_length=20, default="Medium")  # 'Easy', 'Medium', 'Hard'
    question_count = me.IntField(default=5)
    input_mode = me.StringField(default="text", max_length=20)  # 'text' or 'voice'
    status = me.StringField(default="in_progress", max_length=20)  # 'in_progress', 'completed', 'abandoned'
    evaluation_mode = me.StringField(default="Rule-Based (Offline Demo)", max_length=60)
    total_score = me.FloatField(default=0.0)  # Final score after penalties (0.0 to 10.0)
    raw_score = me.FloatField(default=0.0)    # Evaluated score before penalties
    tab_switch_count = me.IntField(default=0)
    violations_count = me.IntField(default=0)
    proctoring_penalty = me.FloatField(default=0.0)
    integrity_score = me.FloatField(default=100.0)
    resume_text = me.StringField()
    resume_filename = me.StringField()
    question_ids_json = me.StringField(default="[]")
    started_at = me.DateTimeField(default=datetime.utcnow)
    completed_at = me.DateTimeField()

    @property
    def question_ids(self):
        try:
            return json.loads(self.question_ids_json) if self.question_ids_json else []
        except Exception:
            return []

    @question_ids.setter
    def question_ids(self, value):
        self.question_ids_json = json.dumps(value if isinstance(value, list) else [])

    @property
    def candidate(self):
        from .user import User
        return User.query.get(self.user_id)

    @property
    def responses(self):
        from .interview import Response
        return Response.query.filter_by(interview_id=self.id).order_by("id")

    @property
    def result(self):
        from .result import Result
        return Result.query.filter_by(interview_id=self.id).first()

    @property
    def proctoring_logs(self):
        from .interview import ProctoringLog
        return ProctoringLog.query.filter_by(interview_id=self.id).order_by("-timestamp")

    def to_dict(self):
        """Serialize interview object."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "question_count": self.question_count,
            "input_mode": self.input_mode,
            "status": self.status,
            "evaluation_mode": self.evaluation_mode,
            "total_score": round(self.total_score, 1) if self.total_score is not None else 0.0,
            "percentage": round(self.total_score * 10, 1) if self.total_score is not None else 0.0,
            "started_at": self.started_at.strftime("%Y-%m-%d %H:%M:%S") if self.started_at else None,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.completed_at else None,
            "answered_count": self.responses.count(),
        }

    def __repr__(self):
        return f"<Interview {self.id}: {self.category} ({self.status})>"


class Response(BaseDocument):
    """Candidate response and AI evaluation in MongoDB."""

    meta = {"collection": "responses", "strict": False}

    id = me.SequenceField(primary_key=True)
    interview_id = me.IntField(required=True)
    question_id = me.IntField(required=True)
    answer_text = me.StringField(required=True)

    # Structured Rubric Scores (0 to 10)
    correctness_score = me.FloatField(default=0.0)
    relevance_score = me.FloatField(default=0.0)
    completeness_score = me.FloatField(default=0.0)
    clarity_score = me.FloatField(default=0.0)
    overall_score = me.FloatField(default=0.0)

    # Detailed Feedback & Explanations
    feedback = me.StringField()
    strengths_json = me.StringField(default="[]")
    weaknesses_json = me.StringField(default="[]")
    suggested_answer = me.StringField()
    improvement_tips_json = me.StringField(default="[]")
    created_at = me.DateTimeField(default=datetime.utcnow)

    @property
    def question(self):
        from .question import Question
        return Question.query.get(self.question_id)

    @property
    def interview(self):
        return Interview.query.get(self.interview_id)

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
    def improvement_tips(self):
        try:
            return json.loads(self.improvement_tips_json) if self.improvement_tips_json else []
        except Exception:
            return []

    @improvement_tips.setter
    def improvement_tips(self, value):
        self.improvement_tips_json = json.dumps(value if isinstance(value, list) else [])

    def to_dict(self):
        q = self.question
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "question_id": self.question_id,
            "question_text": q.question_text if q else "",
            "answer_text": self.answer_text,
            "correctness": round(self.correctness_score, 1),
            "relevance": round(self.relevance_score, 1),
            "completeness": round(self.completeness_score, 1),
            "clarity": round(self.clarity_score, 1),
            "overall_score": round(self.overall_score, 1),
            "feedback": self.feedback,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggested_answer": self.suggested_answer,
            "improvement_tips": self.improvement_tips,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

    def __repr__(self):
        return f"<Response {self.id}: Q{self.question_id} Score={self.overall_score}>"


class ProctoringLog(BaseDocument):
    """Proctoring events and violations in MongoDB."""

    meta = {"collection": "proctoring_logs", "strict": False}

    id = me.SequenceField(primary_key=True)
    interview_id = me.IntField(required=True)
    event_type = me.StringField(required=True, max_length=50)
    severity = me.StringField(default="medium", max_length=20)
    description = me.StringField(required=True)
    penalty_applied = me.FloatField(default=0.0)
    timestamp = me.DateTimeField(default=datetime.utcnow)

    @property
    def interview(self):
        return Interview.query.get(self.interview_id)

    def to_dict(self):
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "description": self.description,
            "penalty_applied": self.penalty_applied,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None,
        }

    def __repr__(self):
        return f"<ProctoringLog {self.id}: {self.event_type} (-{self.penalty_applied})>"
