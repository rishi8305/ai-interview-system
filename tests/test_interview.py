from models import Interview, Question, Response, Result


def test_interview_setup_and_creation(auth_candidate, app):
    """Test creating an interview session."""
    response = auth_candidate.post(
        "/interview/setup",
        data={
            "category": "Technical",
            "topic": "Python",
            "difficulty": "Easy",
            "question_count": "5",
            "input_mode": "text",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Question 1 of" in response.data

    with app.app_context():
        interview = Interview.query.filter_by(topic="Python").first()
        assert interview is not None
        assert interview.status == "in_progress"
        assert len(interview.question_ids) > 0


def test_answer_submission_and_evaluation(auth_candidate, app):
    """Test submitting answer and receiving structured evaluation."""
    # Create interview
    auth_candidate.post(
        "/interview/setup",
        data={"category": "Technical", "topic": "Python", "difficulty": "Easy", "question_count": "5", "input_mode": "text"},
    )

    with app.app_context():
        interview = Interview.query.first()
        q_id = interview.question_ids[0]

    # Submit answer via JSON API
    response = auth_candidate.post(
        f"/interview/{interview.id}/submit",
        json={
            "question_id": q_id,
            "answer_text": "A list comprehension is a concise syntactic construct to build lists by applying an expression to each item in an iterable collection.",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "status" in data
    assert data["status"] in ("next", "completed")

    with app.app_context():
        saved_resp = Response.query.filter_by(interview_id=interview.id, question_id=q_id).first()
        assert saved_resp is not None
        assert saved_resp.overall_score > 0
        assert saved_resp.correctness_score > 0
        assert saved_resp.relevance_score > 0
        assert saved_resp.completeness_score > 0
        assert saved_resp.clarity_score > 0
        assert len(saved_resp.feedback) > 0


def test_prevent_duplicate_submission(auth_candidate, app):
    """Test duplicate submission for same question is blocked."""
    auth_candidate.post(
        "/interview/setup",
        data={"category": "Technical", "topic": "Python", "difficulty": "Easy", "question_count": "5", "input_mode": "text"},
    )

    with app.app_context():
        interview = Interview.query.first()
        q_id = interview.question_ids[0]

    # First submission
    auth_candidate.post(
        f"/interview/{interview.id}/submit",
        json={"question_id": q_id, "answer_text": "First answer"},
    )

    # Second submission for same question
    response = auth_candidate.post(
        f"/interview/{interview.id}/submit",
        json={"question_id": q_id, "answer_text": "Second duplicate answer"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "already been answered" in data["error"]


def test_unauthorized_interview_access(client, app):
    """Test candidate cannot access or submit another candidate's interview."""
    with app.app_context():
        # Interview belonging to candidate #1
        interview = Interview(user_id=1, category="Technical", difficulty="Easy", status="in_progress")
        interview.question_ids = [1]
        from models import db
        db.session.add(interview)
        db.session.commit()
        int_id = interview.id

    # Log in as other candidate #3
    client.post("/login", data={"email": "other@test.com", "password": "Other@123"})

    # Attempt to view live interview of candidate #1
    response = client.get(f"/interview/{int_id}/live")
    assert response.status_code == 403

    # Attempt to submit to interview of candidate #1
    submit_resp = client.post(
        f"/interview/{int_id}/submit",
        json={"question_id": 1, "answer_text": "Unauthorized hack"},
    )
    assert submit_resp.status_code == 403
