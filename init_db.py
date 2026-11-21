"""Database initialization and seeding script for MongoDB."""

import os
from flask import Flask
from config import Config
from models import db, User, Question, Interview, Response, Result
from seed_questions import SEED_QUESTIONS


def auto_migrate_columns(app: Flask):
    """No-op for MongoDB schema-less documents."""
    pass


def seed_database(app: Flask):
    """Seed default administrator, sample candidate, and questions in MongoDB."""
    with app.app_context():
        # Ensure database is connected
        

        # Seed Default Administrator
        admin_email = "admin@aiinterview.com"
        existing_admin = User.query.filter_by(email=admin_email).first()
        if not existing_admin:
            admin = User(
                name="System Administrator",
                email=admin_email,
                role="admin",
            )
            admin.set_password("Admin@123")
            admin.save()
            print(f"[+] Created default Admin account: {admin_email} / Admin@123")
        else:
            print(f"[*] Admin account {admin_email} already exists in MongoDB.")

        # Seed Demo Candidate
        candidate_email = "candidate@aiinterview.com"
        existing_candidate = User.query.filter_by(email=candidate_email).first()
        if not existing_candidate:
            candidate = User(
                name="Demo Candidate",
                email=candidate_email,
                role="candidate",
            )
            candidate.set_password("Candidate@123")
            candidate.save()
            print(f"[+] Created demo Candidate account: {candidate_email} / Candidate@123")
        else:
            print(f"[*] Candidate account {candidate_email} already exists in MongoDB.")

        # Seed Questions
        questions_added = 0
        for q_data in SEED_QUESTIONS:
            exists = Question.query.filter_by(
                question_text=q_data["question_text"]
            ).first()
            if not exists:
                q = Question(
                    category=q_data["category"],
                    topic=q_data.get("topic"),
                    difficulty=q_data["difficulty"],
                    question_text=q_data["question_text"],
                    reference_answer=q_data["reference_answer"],
                    keywords=q_data["keywords"],
                )
                q.save()
                questions_added += 1

        print(f"[+] Questions seeded: {questions_added} new questions added. Total in MongoDB: {Question.query.count()}")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    seed_database(app)
    print("[+] Database initialization complete!")
