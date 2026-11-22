import re
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from models import db, User
from services import EmailService

auth_bp = Blueprint("auth", __name__)


def generate_reset_token(email: str) -> str:
    """Generate a secure, time-sensitive signed token for password reset."""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="password-reset-salt")


def verify_reset_token(token: str, max_age: int = 1800) -> str:
    """Verify signed password reset token. Expires after max_age seconds (default 30 min)."""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=max_age)
        return email
    except (BadSignature, SignatureExpired):
        return None


def admin_required(f):
    """Decorator to restrict access strictly to administrators."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        if not current_user.is_admin:
            flash("Administrator privileges are required to access that area.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Candidate registration route."""
    if current_user.is_authenticated:
        return redirect(url_for("candidate.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Form Validation
        if not name or len(name) < 2:
            flash("Please enter your full name (minimum 2 characters).", "warning")
            return render_template("register.html", name=name, email=email)

        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            flash("Please enter a valid email address.", "warning")
            return render_template("register.html", name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters in length.", "warning")
            return render_template("register.html", name=name, email=email)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "warning")
            return render_template("register.html", name=name, email=email)

        # Duplicate email check
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email address already exists. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        # Create candidate account (Admin role is strictly forbidden from self-registration)
        new_user = User(
            name=name,
            email=email,
            role="candidate",
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login route supporting candidates and administrators."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("candidate.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not email or not password:
            flash("Please enter both email address and password.", "warning")
            return render_template("login.html", email=email)

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}!", "success")

            next_page = request.args.get("next")
            if next_page and not next_page.startswith("//") and not next_page.startswith("http"):
                return redirect(next_page)

            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("candidate.dashboard"))

        flash("Invalid email or password. Please try again.", "danger")
        return render_template("login.html", email=email)

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out current user."""
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password request page: verifies registered email and sends reset link."""
    if current_user.is_authenticated:
        return redirect(url_for("candidate.dashboard"))

    reset_link = None
    email_entered = ""
    email_sent = False

    if request.method == "POST":
        email_entered = request.form.get("email", "").strip().lower()

        if not email_entered:
            flash("Please enter your registered email address.", "warning")
            return render_template("forgot_password.html")

        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email_entered):
            flash("Please enter a valid email address.", "warning")
            return render_template("forgot_password.html", email=email_entered)

        # 1. VERIFY IF PERSON IS REGISTERED IN DATABASE
        user = User.query.filter_by(email=email_entered).first()

        if not user:
            # Unregistered email
            flash("No registered account found with that email address. Please check your spelling or register a new account.", "danger")
            return render_template("forgot_password.html", email=email_entered)

        # 2. REGISTERED PERSON CONFIRMED -> Generate signed reset token
        token = generate_reset_token(user.email)
        reset_link = url_for("auth.reset_password", token=token, _external=True)

        # 3. DISPATCH RESET LINK TO REGISTERED EMAIL VIA SMTP
        sent_success, send_msg = EmailService.send_password_reset_email(
            to_email=user.email,
            recipient_name=user.name,
            reset_url=reset_link,
        )

        email_sent = True
        current_app.logger.info(f"[PASSWORD RESET DISPATCH] User: {user.email} | URL: {reset_link}")

        if sent_success:
            flash(f"A password reset link has been dispatched to your registered email ({user.email}). Please check your inbox and spam folder.", "success")
        else:
            # When SMTP is not configured in .env, record in log and notify user
            if not current_app.config.get("MAIL_SERVER") or not current_app.config.get("MAIL_USERNAME"):
                flash(
                    f"Password reset request received for {user.email}. (To receive actual emails in your Gmail inbox, add your Gmail App Password to MAIL_USERNAME and MAIL_PASSWORD in .env)",
                    "info",
                )
            else:
                flash(f"Could not deliver email: {send_msg}", "warning")

    return render_template(
        "forgot_password.html",
        email=email_entered,
        email_sent=email_sent,
    )


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password with signed secure token."""
    if current_user.is_authenticated:
        return redirect(url_for("candidate.dashboard"))

    email = verify_reset_token(token)
    if not email:
        flash("The password reset link is invalid or has expired (links expire after 30 minutes). Please request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User associated with this reset link no longer exists.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 6:
            flash("New password must be at least 6 characters in length.", "warning")
            return render_template("reset_password.html", token=token, email=email)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "warning")
            return render_template("reset_password.html", token=token, email=email)

        user.set_password(password)
        user.save()

        flash("Your password has been successfully reset! You can now log in with your new credentials.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token, email=email)
