import pytest
from app import create_app
from config import TestConfig
from models import db, User, Question, Interview, Response, Result


@pytest.fixture
def app():
    """Create test application instance with in-memory database."""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()

        # Create Admin
        admin = User(name="Test Admin", email="admin@test.com", role="admin")
        admin.set_password("Admin@123")
        db.session.add(admin)

        # Create Candidate
        candidate = User(name="Test Candidate", email="candidate@test.com", role="candidate")
        candidate.set_password("Candidate@123")
        db.session.add(candidate)

        # Create Another Candidate (for cross-user authorization tests)
        other_candidate = User(name="Other Candidate", email="other@test.com", role="candidate")
        other_candidate.set_password("Other@123")
        db.session.add(other_candidate)

        # Create Sample Questions
        q1 = Question(
            category="Technical",
            topic="Python",
            difficulty="Easy",
            question_text="What is a list comprehension in Python?",
            reference_answer="A concise way to create lists using [expr for item in iterable].",
            keywords="list, comprehension, syntax, concise, iterable",
        )
        q2 = Question(
            category="Technical",
            topic="Python",
            difficulty="Medium",
            question_text="Explain Python generators and the yield statement.",
            reference_answer="Generators produce values on demand using yield, maintaining state between calls.",
            keywords="generator, yield, iterator, lazy, memory",
        )
        q3 = Question(
            category="HR",
            topic="Behavioral",
            difficulty="Easy",
            question_text="Tell me about yourself and your career goals.",
            reference_answer="Explain current education, projects, skills, and future aspirations.",
            keywords="goals, skills, projects, future, background",
        )
        db.session.add_all([q1, q2, q3])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def auth_candidate(client):
    """Log in candidate and return client."""
    client.post("/login", data={"email": "candidate@test.com", "password": "Candidate@123"})
    return client


@pytest.fixture
def auth_admin(client):
    """Log in admin and return client."""
    client.post("/login", data={"email": "admin@test.com", "password": "Admin@123"})
    return client
