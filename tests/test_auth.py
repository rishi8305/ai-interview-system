from models import User


def test_candidate_registration(client, app):
    """Test successful candidate registration."""
    response = client.post(
        "/register",
        data={
            "name": "New Candidate",
            "email": "newbie@test.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Account created successfully" in response.data

    with app.app_context():
        user = User.query.filter_by(email="newbie@test.com").first()
        assert user is not None
        assert user.role == "candidate"
        assert user.check_password("Password123")


def test_duplicate_registration_prevention(client):
    """Test duplicate email prevention during registration."""
    response = client.post(
        "/register",
        data={
            "name": "Duplicate User",
            "email": "candidate@test.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=True,
    )
    assert b"An account with this email address already exists" in response.data


def test_password_mismatch_registration(client):
    """Test password mismatch validation."""
    response = client.post(
        "/register",
        data={
            "name": "Mismatch User",
            "email": "mismatch@test.com",
            "password": "Password123",
            "confirm_password": "PasswordDifferent",
        },
    )
    assert b"Passwords do not match" in response.data


def test_candidate_login_success(client):
    """Test successful candidate login."""
    response = client.post(
        "/login",
        data={"email": "candidate@test.com", "password": "Candidate@123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, Test Candidate" in response.data


def test_admin_login_success(client):
    """Test successful admin login redirects to admin dashboard."""
    response = client.post(
        "/login",
        data={"email": "admin@test.com", "password": "Admin@123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Administrative Overview" in response.data


def test_invalid_credentials(client):
    """Test login failure with wrong password."""
    response = client.post(
        "/login",
        data={"email": "candidate@test.com", "password": "WrongPassword"},
        follow_redirects=True,
    )
    assert b"Invalid email or password" in response.data


def test_logout(auth_candidate):
    """Test user logout."""
    response = auth_candidate.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out successfully" in response.data


def test_forgot_password_get(client):
    """Test GET /forgot_password renders form."""
    response = client.get("/forgot_password")
    assert response.status_code == 200
    assert b"Reset Your Password" in response.data
    assert b"Send Reset Link" in response.data


def test_forgot_password_post_valid_email(client):
    """Test POST /forgot_password confirms registered user and dispatches email without exposing link on web page."""
    response = client.post(
        "/forgot_password",
        data={"email": "candidate@test.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Check Your Email Inbox" in response.data
    # Ensure the reset URL is NOT printed on the public web page
    assert b"/reset_password/" not in response.data


def test_forgot_password_post_nonexistent_email(client):
    """Test POST /forgot_password rejects unregistered email."""
    response = client.post(
        "/forgot_password",
        data={"email": "nonexistent@test.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"No registered account found" in response.data


def test_reset_password_flow(client, app):
    """Test full reset password flow with signed token."""
    with app.app_context():
        from routes.auth import generate_reset_token
        token = generate_reset_token("candidate@test.com")

    # GET reset password page
    get_res = client.get(f"/reset_password/{token}")
    assert get_res.status_code == 200
    assert b"Set New Password" in get_res.data
    assert b"candidate@test.com" in get_res.data

    # POST new password
    post_res = client.post(
        f"/reset_password/{token}",
        data={"password": "NewSecretPassword123", "confirm_password": "NewSecretPassword123"},
        follow_redirects=True,
    )
    assert post_res.status_code == 200
    assert b"successfully reset" in post_res.data

    # Verify user can log in with new password
    login_res = client.post(
        "/login",
        data={"email": "candidate@test.com", "password": "NewSecretPassword123"},
        follow_redirects=True,
    )
    assert login_res.status_code == 200
    assert b"Welcome back" in login_res.data


def test_reset_password_invalid_token(client):
    """Test accessing reset password with tampered or expired token."""
    response = client.get("/reset_password/invalid-tampered-token", follow_redirects=True)
    assert response.status_code == 200
    assert b"invalid or has expired" in response.data


def test_email_service_fallback_when_smtp_unconfigured(app):
    """Ensure EmailService safely handles unconfigured SMTP in local/test environments."""
    with app.app_context():
        from services import EmailService
        success, msg = EmailService.send_password_reset_email(
            to_email="candidate@test.com",
            recipient_name="Test Candidate",
            reset_url="http://127.0.0.1:5000/reset_password/mock-token",
        )
        assert success is False
        assert "not configured" in msg.lower()
