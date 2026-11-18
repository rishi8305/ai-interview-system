from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models import db, User, Question, Interview, Response, Result
from routes.auth import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Admin overview dashboard."""
    total_candidates = User.query.filter_by(role="candidate").count()
    total_interviews = Interview.query.count()
    completed_interviews = Interview.query.filter_by(status="completed").all()

    avg_score = (
        round(sum(i.total_score for i in completed_interviews) / len(completed_interviews), 1)
        if completed_interviews
        else 0.0
    )
    avg_percentage = round(avg_score * 10, 1)

    # Category stats
    categories = ["Technical", "HR", "Aptitude"]
    category_counts = {
        c: Interview.query.filter_by(category=c).count() for c in categories
    }

    # Recent activity: latest 10 interviews across the platform
    recent_activity = (
        Interview.query.order_by(Interview.started_at.desc()).limit(10).all()
    )

    # Total questions in system
    total_questions = Question.query.count()

    return render_template(
        "admin/dashboard.html",
        total_candidates=total_candidates,
        total_interviews=total_interviews,
        avg_score=avg_score,
        avg_percentage=avg_percentage,
        category_counts=category_counts,
        recent_activity=recent_activity,
        total_questions=total_questions,
    )


@admin_bp.route("/questions", methods=["GET", "POST"])
@login_required
@admin_required
def questions():
    """Admin question management: list, filter, and add questions."""
    if request.method == "POST":
        category = request.form.get("category", "").strip()
        topic = request.form.get("topic", "").strip() or None
        difficulty = request.form.get("difficulty", "Medium").strip()
        question_text = request.form.get("question_text", "").strip()
        reference_answer = request.form.get("reference_answer", "").strip()
        keywords = request.form.get("keywords", "").strip()

        if not category or not question_text:
            flash("Category and Question Text are required fields.", "warning")
            return redirect(url_for("admin.questions"))

        q = Question(
            category=category,
            topic=topic,
            difficulty=difficulty,
            question_text=question_text,
            reference_answer=reference_answer,
            keywords=keywords,
        )
        db.session.add(q)
        db.session.commit()
        flash("New interview question added successfully!", "success")
        return redirect(url_for("admin.questions"))

    # Filtering
    cat_filter = request.args.get("category", "").strip()
    diff_filter = request.args.get("difficulty", "").strip()
    search = request.args.get("search", "").strip()

    query = Question.query
    if cat_filter:
        query = query.filter_by(category=cat_filter)
    if diff_filter:
        query = query.filter_by(difficulty=diff_filter)
    if search:
        query = query.filter(Question.question_text.ilike(f"%{search}%"))

    question_list = query.order_by(Question.created_at.desc()).all()

    technical_topics = [
        "Python", "Java", "SQL", "DBMS", "OOP",
        "Data Structures", "Machine Learning",
        "Artificial Intelligence", "Web Development"
    ]

    return render_template(
        "admin/questions.html",
        questions=question_list,
        current_category=cat_filter,
        current_difficulty=diff_filter,
        search_query=search,
        technical_topics=technical_topics,
    )


@admin_bp.route("/questions/<int:question_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_question(question_id):
    """Edit existing question details."""
    q = Question.query.get_or_404(question_id)
    q.category = request.form.get("category", q.category).strip()
    q.topic = request.form.get("topic", q.topic).strip() or None
    q.difficulty = request.form.get("difficulty", q.difficulty).strip()
    q.question_text = request.form.get("question_text", q.question_text).strip()
    q.reference_answer = request.form.get("reference_answer", q.reference_answer).strip()
    q.keywords = request.form.get("keywords", q.keywords).strip()

    db.session.commit()
    flash(f"Question #{q.id} updated successfully.", "success")
    return redirect(url_for("admin.questions"))


@admin_bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_question(question_id):
    """Delete question from database."""
    q = Question.query.get_or_404(question_id)
    db.session.delete(q)
    db.session.commit()
    flash(f"Question #{question_id} deleted successfully.", "info")
    return redirect(url_for("admin.questions"))


@admin_bp.route("/candidates")
@login_required
@admin_required
def candidates():
    """Admin candidate management: view candidates, search, stats."""
    search = request.args.get("search", "").strip()
    query = User.query.filter_by(role="candidate")

    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )

    candidate_list = query.order_by(User.created_at.desc()).all()

    # Precalculate candidate metrics
    candidate_data = []
    for c in candidate_list:
        interviews = c.interviews.filter_by(status="completed").all()
        count = len(interviews)
        avg = round(sum(i.total_score for i in interviews) / count, 1) if count else 0.0
        candidate_data.append({
            "user": c,
            "interview_count": count,
            "avg_score": avg,
            "avg_percentage": round(avg * 10, 1),
            "latest_interview": interviews[-1] if interviews else None,
        })

    return render_template(
        "admin/candidates.html",
        candidates=candidate_data,
        search_query=search,
    )


@admin_bp.route("/candidates/<int:user_id>")
@login_required
@admin_required
def candidate_detail(user_id):
    """View full interview profile of a specific candidate."""
    candidate = User.query.get_or_404(user_id)
    interviews = candidate.interviews.order_by(Interview.started_at.desc()).all()

    completed = [i for i in interviews if i.status == "completed"]
    avg_score = (
        round(sum(i.total_score for i in completed) / len(completed), 1)
        if completed
        else 0.0
    )

    return render_template(
        "admin/candidate_detail.html",
        candidate=candidate,
        interviews=interviews,
        avg_score=avg_score,
        total_completed=len(completed),
    )


@admin_bp.route("/candidates/<int:user_id>/edit_password", methods=["POST"])
@login_required
@admin_required
def edit_candidate_password(user_id):
    """Admin can change or reset password for any candidate."""
    candidate = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if len(new_password) < 6:
        flash("Password must be at least 6 characters in length.", "warning")
        return redirect(request.referrer or url_for("admin.candidates"))

    if new_password != confirm_password:
        flash("Passwords do not match. Please re-enter.", "warning")
        return redirect(request.referrer or url_for("admin.candidates"))

    candidate.set_password(new_password)
    db.session.commit()
    flash(f"Password for candidate '{candidate.name}' ({candidate.email}) was updated successfully by Admin.", "success")
    return redirect(request.referrer or url_for("admin.candidates"))


@admin_bp.route("/interviews")
@login_required
@admin_required
def interviews():
    """View and filter all platform interviews."""
    cat_filter = request.args.get("category", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Interview.query
    if cat_filter:
        query = query.filter_by(category=cat_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    interview_list = query.order_by(Interview.started_at.desc()).all()

    return render_template(
        "admin/interviews.html",
        interviews=interview_list,
        current_category=cat_filter,
        current_status=status_filter,
    )


@admin_bp.route("/interviews/<int:interview_id>")
@login_required
@admin_required
def interview_detail(interview_id):
    """Admin inspect candidate interview results and AI response evaluations."""
    interview = Interview.query.get_or_404(interview_id)
    result = interview.result
    responses = interview.responses.all()

    return render_template(
        "admin/interview_detail.html",
        interview=interview,
        result=result,
        responses=responses,
    )


@admin_bp.route("/profile", methods=["GET", "POST"])
@login_required
@admin_required
def profile():
    """Admin profile settings and password change."""
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_info":
            name = request.form.get("name", "").strip()
            if not name or len(name) < 2:
                flash("Admin name must be at least 2 characters.", "warning")
            else:
                current_user.name = name
                db.session.commit()
                flash("Admin name updated successfully!", "success")

        elif action == "change_password":
            current_pass = request.form.get("current_password", "")
            new_pass = request.form.get("new_password", "")
            confirm_pass = request.form.get("confirm_password", "")

            if not current_user.check_password(current_pass):
                flash("Current password is incorrect.", "danger")
            elif len(new_pass) < 6:
                flash("New password must be at least 6 characters in length.", "warning")
            elif new_pass != confirm_pass:
                flash("New passwords do not match.", "warning")
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                flash("Admin password updated successfully! Please use your new password next time you sign in.", "success")

        return redirect(url_for("admin.profile"))

    total_candidates = User.query.filter_by(role="candidate").count()
    total_interviews = Interview.query.count()

    return render_template(
        "admin/profile.html",
        total_candidates=total_candidates,
        total_interviews=total_interviews,
    )
