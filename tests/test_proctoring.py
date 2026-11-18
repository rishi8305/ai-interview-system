import base64
import numpy as np
import cv2
from models import db, Interview, ProctoringLog, Result
from services import ProctorService, ReportService


def test_tab_switch_logging_and_penalty(auth_candidate, app):
    """Test tab switch endpoint increments count, creates log, and calculates penalty."""
    with app.app_context():
        interview = Interview(user_id=2, category="Technical", difficulty="Easy", status="in_progress", total_score=8.0)
        interview.question_ids = [1]
        db.session.add(interview)
        db.session.commit()
        int_id = interview.id

    # 1. First tab switch
    res1 = auth_candidate.post(f"/interview/{int_id}/proctor/tab_switch")
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["tab_switches"] == 1
    assert data1["penalty_applied"] == 0.5
    assert data1["penalty_percentage"] == 5.0
    assert data1["integrity_score"] == 95.0

    # 2. Second tab switch
    res2 = auth_candidate.post(f"/interview/{int_id}/proctor/tab_switch")
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["tab_switches"] == 2
    assert data2["penalty_percentage"] == 10.0
    assert data2["integrity_score"] == 90.0

    with app.app_context():
        logs = ProctoringLog.query.filter_by(interview_id=int_id).all()
        assert len(logs) == 2
        assert logs[0].event_type == "tab_switch"
        assert logs[0].penalty_applied == 0.5


def test_mark_reduction_calculation(app):
    """Test score reduction algorithm when finalizing interview with tab switches."""
    with app.app_context():
        interview = Interview(
            user_id=2,
            category="Technical",
            difficulty="Easy",
            status="in_progress",
            raw_score=8.0,
            total_score=8.0,
            tab_switch_count=3,  # 3 switches = 1.5 pt deduction (15%)
            violations_count=1,   # 1 violation = 0.5 pt deduction (5%)
        )
        db.session.add(interview)
        db.session.commit()

        metrics = ProctorService.compute_integrity_and_penalties(interview)
        # Raw = 8.0, Total penalty = 1.5 + 0.5 = 2.0 pts (20%)
        # Net score = 6.0 / 10 (60%)
        # Integrity = 80%
        assert metrics["raw_score"] == 8.0
        assert metrics["tab_switches"] == 3
        assert metrics["tab_penalty"] == 1.5
        assert metrics["violation_penalty"] == 0.5
        assert metrics["total_penalty"] == 2.0
        assert metrics["net_score"] == 6.0
        assert metrics["net_percentage"] == 60.0
        assert metrics["integrity_score"] == 80.0


def test_proctor_log_event(auth_candidate, app):
    """Test logging proctoring violation events (e.g. prohibited objects)."""
    with app.app_context():
        interview = Interview(user_id=2, category="Technical", difficulty="Easy", status="in_progress")
        interview.question_ids = [1]
        db.session.add(interview)
        db.session.commit()
        int_id = interview.id

    res = auth_candidate.post(
        f"/interview/{int_id}/proctor/log_event",
        json={
            "event_type": "prohibited_object",
            "description": "Cell phone detected in candidate frame.",
            "severity": "high",
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["violations_count"] == 1
    assert data["total_penalty"] == 0.5

    with app.app_context():
        log = ProctoringLog.query.filter_by(interview_id=int_id, event_type="prohibited_object").first()
        assert log is not None
        assert "Cell phone" in log.description


def test_opencv_frame_analyzer():
    """Test OpenCV server frame analyzer on synthetic frame."""
    # Create a synthetic 100x100 blank image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buffer = cv2.imencode(".jpg", img)
    base64_str = base64.b64encode(buffer).decode("utf-8")

    result = ProctorService.analyze_frame_base64(base64_str)
    assert result["valid"] is True
    assert "faces_count" in result
    assert result["faces_count"] == 0
    assert result["status"] == "no_face"
    assert result["violation"] is True


def test_pdf_report_with_proctoring_data(app):
    """Test PDF generation includes proctoring and tab switch audit section."""
    with app.app_context():
        interview = Interview(
            user_id=2,
            category="Technical",
            difficulty="Medium",
            status="completed",
            raw_score=9.0,
            total_score=8.0,
            tab_switch_count=2,
            violations_count=0,
            proctoring_penalty=1.0,
            integrity_score=90.0,
        )
        interview.question_ids = [1]
        db.session.add(interview)
        db.session.commit()

        pdf_buffer = ReportService.generate_interview_pdf(interview)
        pdf_bytes = pdf_buffer.getvalue()
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 2000
