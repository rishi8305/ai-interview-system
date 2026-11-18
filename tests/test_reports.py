from services import ReportService
from models import db, Interview, Question, Response, Result


def test_pdf_report_generation(app):
    """Test ReportLab generates valid PDF document buffer."""
    with app.app_context():
        # Setup interview with response and result
        interview = Interview(user_id=1, category="Technical", topic="Python", difficulty="Easy", status="completed", total_score=8.5)
        interview.question_ids = [1]
        db.session.add(interview)
        db.session.commit()

        q = Question.query.first()
        resp = Response(
            interview_id=interview.id,
            question_id=q.id,
            answer_text="A list comprehension builds lists in Python concisely.",
            correctness_score=9.0,
            relevance_score=8.5,
            completeness_score=8.0,
            clarity_score=8.5,
            overall_score=8.6,
            feedback="Very clear answer.",
            suggested_answer="Model reference answer.",
        )
        resp.strengths = ["Accurate syntax"]
        resp.weaknesses = ["Could add more examples"]
        db.session.add(resp)

        result = Result(
            interview_id=interview.id,
            user_id=1,
            total_score=8.6,
            percentage=86.0,
            correctness_avg=9.0,
            relevance_avg=8.5,
            completeness_avg=8.0,
            clarity_avg=8.5,
        )
        result.strengths = ["Clear conceptual grasp"]
        result.recommendations = ["Continue with advanced algorithms"]
        db.session.add(result)
        db.session.commit()

        # Generate PDF buffer
        pdf_buffer = ReportService.generate_interview_pdf(interview)
        assert pdf_buffer is not None
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 1000
        # Valid PDF files start with %PDF-
        assert pdf_bytes.startswith(b"%PDF-")


def test_pdf_download_route(auth_candidate, app):
    """Test PDF download endpoint returns 200 with application/pdf header."""
    with app.app_context():
        # Interview belonging to candidate
        interview = Interview(user_id=2, category="HR", difficulty="Easy", status="completed", total_score=7.0)
        interview.question_ids = [3]
        db.session.add(interview)
        db.session.commit()
        int_id = interview.id

    response = auth_candidate.get(f"/interview/{int_id}/pdf")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert "attachment" in response.headers.get("Content-Disposition", "")
