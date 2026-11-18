import io
import zipfile
import pytest
from flask import url_for
from models import db, User, Interview, Question, Response, Result
from services import ResumeService


def test_resume_extract_skills():
    """Verify keyword extraction accurately detects technical skills."""
    sample_text = """
    Software Engineer with 3 years of experience in Python, Flask, and SQL.
    Built machine learning pipelines using Scikit-Learn and Pandas.
    Deployed containerized microservices with Docker and Git.
    """
    skills = ResumeService.extract_skills(sample_text)
    assert "Python" in skills
    assert "Flask" in skills
    assert "SQL" in skills
    assert "Machine Learning" in skills
    assert "Docker" in skills
    assert "Git" in skills
    # Skills not in text should not be present
    assert "Rust" not in skills
    assert "Kubernetes" not in skills


def test_resume_extract_text_txt():
    """Test text extraction from plain text file bytes."""
    text = "Full Stack Engineer skilled in React and Node.js."
    extracted = ResumeService.extract_text_from_file("my_resume.txt", text.encode("utf-8"))
    assert "React" in extracted
    assert "Node.js" in extracted


def test_resume_extract_text_docx():
    """Test text extraction from synthetic docx byte archive."""
    xml_doc = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>Deep Learning and PyTorch Engineer with AWS experience.</w:t></w:r></w:p></w:body>'
        '</w:document>'
    )
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("word/document.xml", xml_doc.encode("utf-8"))

    docx_bytes = bio.getvalue()
    extracted = ResumeService.extract_text_from_file("candidate_cv.docx", docx_bytes)
    assert "Deep Learning" in extracted
    assert "PyTorch" in extracted


def test_resume_question_generation_rule_based():
    """Verify rule-based question generation synthesizes tailored questions from detected skills."""
    resume_text = "Proficient in Python, SQL, and Docker containerization. Built REST APIs."
    questions = ResumeService.generate_resume_questions(
        resume_text=resume_text,
        count=5,
        difficulty="Medium",
        api_key="",  # forces rule-based engine
    )
    assert len(questions) == 5
    for q in questions:
        assert "question_text" in q and len(q["question_text"]) > 10
        assert "topic" in q and q["topic"].startswith("Resume:")
        assert "difficulty" in q and q["difficulty"] == "Medium"
        assert "reference_answer" in q and len(q["reference_answer"]) > 10
        assert "keywords" in q


def test_resume_setup_get_route(auth_candidate):
    """Test GET /interview/resume_setup renders the upload form."""
    response = auth_candidate.get("/interview/resume_setup")
    assert response.status_code == 200
    assert b"Upload Your Resume" in response.data
    assert b"resumeFileInput" in response.data


def test_resume_setup_post_invalid_extension(auth_candidate):
    """Test POST /interview/resume_setup rejects prohibited file extensions."""
    data = {
        "resume": (io.BytesIO(b"malicious script contents"), "malware.exe"),
        "difficulty": "Medium",
        "question_count": "5",
        "input_mode": "text",
    }
    response = auth_candidate.post("/interview/resume_setup", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    assert b"Unsupported file type" in response.data


def test_resume_setup_post_valid_creates_interview(auth_candidate, app):
    """Test POST /interview/resume_setup creates personalized interview and questions."""
    resume_content = (
        "Experienced Python and React developer. "
        "Built automated testing pipelines, PostgreSQL database designs, and REST APIs."
    )
    data = {
        "resume": (io.BytesIO(resume_content.encode("utf-8")), "my_resume.txt"),
        "difficulty": "Hard",
        "question_count": "5",
        "input_mode": "voice",
    }
    response = auth_candidate.post("/interview/resume_setup", data=data, content_type="multipart/form-data")
    assert response.status_code == 302
    assert "/interview/" in response.headers["Location"]
    assert "/live" in response.headers["Location"]

    with app.app_context():
        candidate = User.query.filter_by(email="candidate@test.com").first()
        interview = Interview.query.filter_by(user_id=candidate.id, resume_filename="my_resume.txt").first()
        assert interview is not None
        assert interview.category == "Technical"
        assert interview.input_mode == "voice"
        assert interview.difficulty == "Hard"
        assert len(interview.question_ids) == 5

        # Verify questions created with is_generated=True
        q = db.session.get(Question, interview.question_ids[0])
        assert q is not None
        assert q.is_generated is True
        assert q.topic.startswith("Resume:")

