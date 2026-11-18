import json
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Interview, Result, User

candidate_bp = Blueprint("candidate", __name__)


@candidate_bp.route("/dashboard")
@login_required
def dashboard():
    """Candidate dashboard displaying performance statistics and analytics."""
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    # Fetch user's completed interviews
    completed_interviews = (
        Interview.query.filter_by(user_id=current_user.id, status="completed")
        .order_by(Interview.completed_at.desc())
        .all()
    )

    total_interviews = len(completed_interviews)
    avg_score = (
        round(sum(i.total_score for i in completed_interviews) / total_interviews, 1)
        if total_interviews > 0
        else 0.0
    )
    avg_percentage = round(avg_score * 10, 1)

    latest_score = (
        round(completed_interviews[0].total_score, 1) if total_interviews > 0 else 0.0
    )
    latest_percentage = round(latest_score * 10, 1)

    # Performance Improvement Data for Chart.js (chronological order)
    chronological = list(reversed(completed_interviews))
    trend_labels = [
        i.completed_at.strftime("%b %d") if i.completed_at else f"Int #{i.id}"
        for i in chronological
    ]
    trend_scores = [round(i.total_score * 10, 1) for i in chronological]

    # Category Breakdown
    categories = ["Technical", "HR", "Aptitude"]
    category_counts = {c: 0 for c in categories}
    category_scores = {c: [] for c in categories}

    for i in completed_interviews:
        cat = i.category
        if cat in category_counts:
            category_counts[cat] += 1
            category_scores[cat].append(i.total_score * 10)

    category_avg_scores = {
        c: (round(sum(category_scores[c]) / len(category_scores[c]), 1) if category_scores[c] else 0.0)
        for c in categories
    }

    # Recent 5 interviews (completed or in-progress)
    recent_interviews = (
        Interview.query.filter_by(user_id=current_user.id)
        .order_by(Interview.started_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_interviews=total_interviews,
        avg_score=avg_score,
        avg_percentage=avg_percentage,
        latest_score=latest_score,
        latest_percentage=latest_percentage,
        recent_interviews=recent_interviews,
        trend_labels=json.dumps(trend_labels),
        trend_scores=json.dumps(trend_scores),
        category_counts=category_counts,
        category_avg_scores=category_avg_scores,
    )


@candidate_bp.route("/history")
@login_required
def history():
    """Candidate interview history page with detailed records and filtering."""
    category_filter = request.args.get("category", "").strip()
    difficulty_filter = request.args.get("difficulty", "").strip()

    query = Interview.query.filter_by(user_id=current_user.id)

    if category_filter:
        query = query.filter_by(category=category_filter)
    if difficulty_filter:
        query = query.filter_by(difficulty=difficulty_filter)

    interviews = query.order_by(Interview.started_at.desc()).all()

    return render_template(
        "history.html",
        interviews=interviews,
        current_category=category_filter,
        current_difficulty=difficulty_filter,
    )


@candidate_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile settings and password change."""
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_info":
            name = request.form.get("name", "").strip()
            if not name or len(name) < 2:
                flash("Name must be at least 2 characters.", "warning")
            else:
                current_user.name = name
                db.session.commit()
                flash("Profile name updated successfully!", "success")

        elif action == "change_password":
            current_pass = request.form.get("current_password", "")
            new_pass = request.form.get("new_password", "")
            confirm_pass = request.form.get("confirm_password", "")

            if not current_user.check_password(current_pass):
                flash("Current password is incorrect.", "danger")
            elif len(new_pass) < 6:
                flash("New password must be at least 6 characters.", "warning")
            elif new_pass != confirm_pass:
                flash("New passwords do not match.", "warning")
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                flash("Password updated successfully!", "success")

        return redirect(url_for("candidate.profile"))

    # Stats for profile card
    total_completed = Interview.query.filter_by(user_id=current_user.id, status="completed").count()

    return render_template("profile.html", total_completed=total_completed)
