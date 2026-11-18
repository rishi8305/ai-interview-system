from models import db, Question, User


def test_candidate_forbidden_from_admin_dashboard(auth_candidate):
    """Ensure candidate role receives 403 Forbidden when accessing admin area."""
    response = auth_candidate.get("/admin/dashboard")
    assert response.status_code == 403


def test_admin_access_dashboard(auth_admin):
    """Ensure admin can access admin dashboard."""
    response = auth_admin.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Administrative Overview" in response.data


def test_admin_add_question(auth_admin, app):
    """Test admin creating a new question in the repository."""
    response = auth_admin.post(
        "/admin/questions",
        data={
            "category": "Technical",
            "topic": "SQL",
            "difficulty": "Easy",
            "question_text": "What is a Primary Key?",
            "reference_answer": "A unique identifier for each record in a database table.",
            "keywords": "unique, identifier, primary key, null",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"New interview question added successfully" in response.data

    with app.app_context():
        q = Question.query.filter_by(question_text="What is a Primary Key?").first()
        assert q is not None
        assert q.category == "Technical"
        assert q.topic == "SQL"


def test_admin_edit_question(auth_admin, app):
    """Test admin editing an existing question."""
    with app.app_context():
        q = Question.query.first()
        q_id = q.id

    response = auth_admin.post(
        f"/admin/questions/{q_id}/edit",
        data={
            "category": "Technical",
            "topic": "Python",
            "difficulty": "Hard",
            "question_text": "Updated question prompt for testing.",
            "reference_answer": "Updated reference.",
            "keywords": "updated, test",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        updated = db.session.get(Question, q_id)
        assert updated.difficulty == "Hard"
        assert updated.question_text == "Updated question prompt for testing."


def test_admin_delete_question(auth_admin, app):
    """Test admin deleting a question."""
    with app.app_context():
        q = Question(category="HR", difficulty="Easy", question_text="Temporary question to delete")
        db.session.add(q)
        db.session.commit()
        q_id = q.id

    response = auth_admin.post(f"/admin/questions/{q_id}/delete", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(Question, q_id) is None


def test_admin_candidate_list(auth_admin):
    """Test admin viewing candidates list."""
    response = auth_admin.get("/admin/candidates")
    assert response.status_code == 200
    assert b"Registered Candidates" in response.data
    assert b"Test Candidate" in response.data


def test_admin_profile_view_and_change_own_password(auth_admin, client, app):
    """Test admin viewing profile and updating their own password."""
    # View profile
    view_res = auth_admin.get("/admin/profile")
    assert view_res.status_code == 200
    assert b"Edit Admin Password" in view_res.data
    assert b"admin@test.com" in view_res.data

    # Change password
    post_res = auth_admin.post(
        "/admin/profile",
        data={
            "action": "change_password",
            "current_password": "Admin@123",
            "new_password": "AdminNewPassword@999",
            "confirm_password": "AdminNewPassword@999",
        },
        follow_redirects=True,
    )
    assert post_res.status_code == 200
    assert b"Admin password updated successfully" in post_res.data

    # Verify admin can log in with new password
    auth_admin.get("/logout")
    login_res = client.post(
        "/login",
        data={"email": "admin@test.com", "password": "AdminNewPassword@999"},
        follow_redirects=True,
    )
    assert login_res.status_code == 200
    assert b"Administrative Overview" in login_res.data


def test_admin_edit_candidate_password(auth_admin, client, app):
    """Test admin changing a candidate's password from admin panel."""
    with app.app_context():
        candidate = User.query.filter_by(email="candidate@test.com").first()
        cand_id = candidate.id

    # Admin changes candidate's password
    res = auth_admin.post(
        f"/admin/candidates/{cand_id}/edit_password",
        data={
            "new_password": "AssignedByAdmin123",
            "confirm_password": "AssignedByAdmin123",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"updated successfully by Admin" in res.data

    # Verify candidate can log in with the new password assigned by admin
    auth_admin.get("/logout")
    login_res = client.post(
        "/login",
        data={"email": "candidate@test.com", "password": "AssignedByAdmin123"},
        follow_redirects=True,
    )
    assert login_res.status_code == 200
    assert b"Welcome back, Test Candidate" in login_res.data


def test_candidate_forbidden_from_admin_edit_password(auth_candidate, app):
    """Ensure candidate role receives 403 when trying to access admin password edit."""
    with app.app_context():
        candidate = User.query.filter_by(email="candidate@test.com").first()
        cand_id = candidate.id

    res = auth_candidate.post(
        f"/admin/candidates/{cand_id}/edit_password",
        data={"new_password": "HackedPassword123", "confirm_password": "HackedPassword123"},
    )
    assert res.status_code == 403
