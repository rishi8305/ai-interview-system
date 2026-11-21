import os
import random
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, send_file, current_app
from flask_login import login_required, current_user
from models import db, Interview, Response, Result, Question, ProctoringLog
from services import EvaluationService, ReportService, ProctorService, ResumeService

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")


@interview_bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    """Interview configuration screen before starting."""
    if request.method == "POST":
        category = request.form.get("category", "Technical")
        topic = request.form.get("topic", "").strip() if category == "Technical" else None
        difficulty = request.form.get("difficulty", "Medium")
        try:
            question_count = int(request.form.get("question_count", 5))
            if question_count not in (5, 10, 15):
                question_count = 5
        except (ValueError, TypeError):
            question_count = 5

        input_mode = request.form.get("input_mode", "text")
        if input_mode not in ("text", "voice"):
            input_mode = "text"

        # Query eligible questions from database
        query = Question.query.filter_by(category=category)
        if topic:
            query = query.filter_by(topic=topic)

        # First attempt: match category, topic, and difficulty
        matched_questions = query.filter_by(difficulty=difficulty).all()

        # If pool has fewer questions than requested, widen to other difficulties in that topic/category
        if len(matched_questions) < question_count:
            additional = query.filter(Question.difficulty != difficulty).all()
            # Combine without duplicates
            matched_pool = matched_questions + [q for q in additional if q not in matched_questions]
        else:
            matched_pool = matched_questions

        # If still empty (edge case), fallback to any question in that category
        if not matched_pool:
            matched_pool = Question.query.filter_by(category=category).all()

        if not matched_pool:
            flash(f"No interview questions are currently available for {category}. Please check back later.", "warning")
            return redirect(url_for("interview.setup"))

        # Randomize selection
        random.shuffle(matched_pool)
        selected_questions = matched_pool[:question_count]
        actual_count = len(selected_questions)

        # Create interview session
        interview = Interview(
            user_id=current_user.id,
            category=category,
            topic=topic,
            difficulty=difficulty,
            question_count=actual_count,
            input_mode=input_mode,
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        interview.question_ids = [q.id for q in selected_questions]

        db.session.add(interview)
        db.session.commit()

        flash(f"New {category} interview started! Complete each question thoughtfully.", "info")
        return redirect(url_for("interview.live", interview_id=interview.id))

    # Available topics for technical category
    technical_topics = [
        "Python", "Java", "SQL", "DBMS", "OOP",
        "Data Structures", "Machine Learning",
        "Artificial Intelligence", "Web Development"
    ]

    return render_template("interview_setup.html", technical_topics=technical_topics)


@interview_bp.route("/<int:interview_id>/live")
@login_required
def live(interview_id):
    """Live interactive interview screen."""
    interview = Interview.query.get_or_404(interview_id)

    # Security check: Candidate can only access their own interview
    if interview.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    # If already completed, redirect to results
    if interview.status == "completed":
        return redirect(url_for("interview.results", interview_id=interview.id))

    question_ids = interview.question_ids
    if not question_ids:
        flash("Interview configuration error: No questions assigned.", "danger")
        return redirect(url_for("candidate.dashboard"))

    # Determine current question index by number of responses submitted so far
    answered_count = interview.responses.count()

    # If all answered, finalize and show results
    if answered_count >= len(question_ids):
        return _finalize_interview(interview)

    current_q_id = question_ids[answered_count]
    current_question = db.session.get(Question, current_q_id)

    if not current_question:
        flash("Error loading question. Please try again.", "danger")
        return redirect(url_for("candidate.dashboard"))

    progress_percentage = round((answered_count / len(question_ids)) * 100)

    return render_template(
        "interview.html",
        interview=interview,
        question=current_question,
        question_index=answered_count + 1,
        total_questions=len(question_ids),
        progress_percentage=progress_percentage,
    )


@interview_bp.route("/<int:interview_id>/submit", methods=["POST"])
@login_required
def submit(interview_id):
    """Submit response to current question and trigger AI evaluation."""
    interview = Interview.query.get_or_404(interview_id)

    if interview.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    if interview.status == "completed":
        return jsonify({
            "status": "completed",
            "redirect": url_for("interview.results", interview_id=interview.id)
        })

    # Read data from JSON or form
    if request.is_json:
        data = request.get_json() or {}
        question_id = data.get("question_id")
        answer_text = data.get("answer_text", "").strip()
    else:
        question_id = request.form.get("question_id")
        answer_text = request.form.get("answer_text", "").strip()

    try:
        question_id = int(question_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid question identifier"}), 400

    question = db.session.get(Question, question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    # Prevent duplicate submission for this question in this interview
    existing_resp = Response.query.filter_by(
        interview_id=interview.id, question_id=question.id
    ).first()
    if existing_resp:
        return jsonify({
            "error": "This question has already been answered.",
            "status": "already_submitted",
            "redirect": url_for("interview.live", interview_id=interview.id)
        }), 400

    # Evaluate response via EvaluationService (AI or labeled rule-based fallback)
    try:
        evaluation, provider_label = EvaluationService.evaluate(question, answer_text)
    except Exception as e:
        # In case of API failure or timeout, return an informative error or fallback
        evaluation, provider_label = EvaluationService._evaluate_rule_based(question, answer_text)
        provider_label = "Rule-Based Offline Evaluator (API Error Fallback)"

    # Update interview's evaluation_mode label
    interview.evaluation_mode = provider_label

    # Save Response
    response_record = Response(
        interview_id=interview.id,
        question_id=question.id,
        answer_text=answer_text,
        correctness_score=evaluation["correctness"],
        relevance_score=evaluation["relevance"],
        completeness_score=evaluation["completeness"],
        clarity_score=evaluation["clarity"],
        overall_score=evaluation["overall_score"],
        feedback=evaluation["feedback"],
        suggested_answer=evaluation["suggested_answer"],
    )
    response_record.strengths = evaluation.get("strengths", [])
    response_record.weaknesses = evaluation.get("weaknesses", [])
    response_record.improvement_tips = evaluation.get("improvement_tips", [])

    db.session.add(response_record)
    db.session.commit()

    # Check if this was the last question
    total_answered = interview.responses.count()
    if total_answered >= len(interview.question_ids):
        _finalize_interview(interview)
        return jsonify({
            "status": "completed",
            "redirect": url_for("interview.results", interview_id=interview.id)
        })

    return jsonify({
        "status": "next",
        "redirect": url_for("interview.live", interview_id=interview.id)
    })


def _finalize_interview(interview):
    """Aggregate all question scores, apply proctoring deductions, and create final Result record."""
    result_data = EvaluationService.aggregate_interview_result(interview)

    # Calculate proctoring reductions (tab switching & frame violations)
    interview.raw_score = result_data["total_score"]
    proctor_metrics = ProctorService.compute_integrity_and_penalties(interview)

    interview.total_score = proctor_metrics["net_score"]
    interview.proctoring_penalty = proctor_metrics["total_penalty"]
    interview.integrity_score = proctor_metrics["integrity_score"]
    interview.status = "completed"
    interview.completed_at = datetime.utcnow()
    interview.save()

    existing_result = Result.query.filter_by(interview_id=interview.id).first()
    if not existing_result:
        result = Result(
            interview_id=interview.id,
            user_id=interview.user_id,
            raw_score=proctor_metrics["raw_score"],
            total_score=proctor_metrics["net_score"],
            percentage=proctor_metrics["net_percentage"],
            proctoring_penalty=proctor_metrics["total_penalty"],
            tab_switch_count=interview.tab_switch_count,
            violations_count=interview.violations_count,
            integrity_score=proctor_metrics["integrity_score"],
            correctness_avg=result_data["correctness_avg"],
            relevance_avg=result_data["relevance_avg"],
            completeness_avg=result_data["completeness_avg"],
            clarity_avg=result_data["clarity_avg"],
        )
        result.strengths = result_data["strengths"]
        result.weaknesses = result_data["weaknesses"]
        result.recommendations = result_data["recommendations"]
        db.session.add(result)
    else:
        existing_result.raw_score = proctor_metrics["raw_score"]
        existing_result.total_score = proctor_metrics["net_score"]
        existing_result.percentage = proctor_metrics["net_percentage"]
        existing_result.proctoring_penalty = proctor_metrics["total_penalty"]
        existing_result.tab_switch_count = interview.tab_switch_count
        existing_result.violations_count = interview.violations_count
        existing_result.integrity_score = proctor_metrics["integrity_score"]
        existing_result.save()

    db.session.commit()

    return redirect(url_for("interview.results", interview_id=interview.id))


@interview_bp.route("/<int:interview_id>/proctor/tab_switch", methods=["POST"])
@login_required
def proctor_tab_switch(interview_id):
    """Handle candidate tab switch event, increment violation count, apply mark penalty."""
    interview = db.session.get(Interview, interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404

    if interview.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    if interview.status == "completed":
        return jsonify({"status": "already_completed"}), 200

    interview.tab_switch_count += 1
    # 0.5 points deduction per tab switch (5% deduction)
    penalty = 0.5

    log = ProctoringLog(
        interview_id=interview.id,
        event_type="tab_switch",
        severity="high",
        description=f"Browser tab switch or window blur detected (Occurrence #{interview.tab_switch_count}). -5% mark penalty applied.",
        penalty_applied=penalty,
    )
    db.session.add(log)
    db.session.commit()

    # Calculate updated metrics
    proctor_metrics = ProctorService.compute_integrity_and_penalties(interview)

    return jsonify({
        "status": "logged",
        "tab_switches": interview.tab_switch_count,
        "penalty_applied": penalty,
        "total_penalty": proctor_metrics["total_penalty"],
        "penalty_percentage": proctor_metrics["penalty_percentage"],
        "integrity_score": proctor_metrics["integrity_score"],
        "warning": f"Tab switch #{interview.tab_switch_count} detected! A {proctor_metrics['penalty_percentage']}% mark deduction will be applied to your final score."
    })


@interview_bp.route("/<int:interview_id>/proctor/log_event", methods=["POST"])
@login_required
def proctor_log_event(interview_id):
    """Log proctoring events such as multiple faces, prohibited object (cell phone, book), or no face."""
    interview = db.session.get(Interview, interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404

    if interview.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    if interview.status == "completed":
        return jsonify({"status": "already_completed"}), 200

    data = request.get_json() or {}
    event_type = data.get("event_type", "unauthorized_activity")
    description = data.get("description", "Integrity warning detected in camera feed.")
    severity = data.get("severity", "medium")

    # High severity violations incur a 0.5 pt penalty (5% deduction)
    penalty = 0.5 if event_type in ("multiple_faces", "prohibited_object") else 0.2
    interview.violations_count += 1

    log = ProctoringLog(
        interview_id=interview.id,
        event_type=event_type,
        severity=severity,
        description=description,
        penalty_applied=penalty,
    )
    db.session.add(log)
    db.session.commit()

    proctor_metrics = ProctorService.compute_integrity_and_penalties(interview)

    return jsonify({
        "status": "logged",
        "violations_count": interview.violations_count,
        "total_penalty": proctor_metrics["total_penalty"],
        "integrity_score": proctor_metrics["integrity_score"],
    })


@interview_bp.route("/<int:interview_id>/proctor/analyze_frame", methods=["POST"])
@login_required
def proctor_analyze_frame(interview_id):
    """Analyze a webcam frame snapshot using server-side OpenCV."""
    interview = db.session.get(Interview, interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404

    if interview.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}
    image_base64 = data.get("image", "")

    if not image_base64:
        return jsonify({"error": "No image data provided"}), 400

    result = ProctorService.analyze_frame_base64(image_base64)

    # If an integrity violation was detected by OpenCV, log it
    if result.get("violation") and interview.status != "completed":
        interview.violations_count += 1
        log = ProctoringLog(
            interview_id=interview.id,
            event_type=result.get("status", "violation"),
            severity=result.get("severity", "medium"),
            description=result.get("message", "Camera frame violation detected by OpenCV analyzer."),
            penalty_applied=result.get("penalty", 0.2),
        )
        db.session.add(log)
        db.session.commit()

    return jsonify(result)


@interview_bp.route("/<int:interview_id>/results")
@login_required
def results(interview_id):
    """Interview results and performance feedback breakdown."""
    interview = Interview.query.get_or_404(interview_id)

    if interview.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    result = interview.result
    if not result:
        # If result wasn't generated yet, generate it now
        _finalize_interview(interview)
        result = interview.result

    responses = interview.responses.all()

    # Rubric labels & values for Chart.js Radar Chart
    rubric_labels = ["Correctness (40%)", "Relevance (25%)", "Completeness (20%)", "Clarity (15%)"]
    rubric_values = [
        result.correctness_avg if result else 0,
        result.relevance_avg if result else 0,
        result.completeness_avg if result else 0,
        result.clarity_avg if result else 0,
    ]

    # Question score progression
    q_labels = [f"Q{idx}" for idx in range(1, len(responses) + 1)]
    q_scores = [round(r.overall_score * 10, 1) for r in responses]

    proctoring_logs = interview.proctoring_logs.all()

    return render_template(
        "results.html",
        interview=interview,
        result=result,
        responses=responses,
        rubric_labels=rubric_labels,
        rubric_values=rubric_values,
        q_labels=q_labels,
        q_scores=q_scores,
        proctoring_logs=proctoring_logs,
    )


@interview_bp.route("/<int:interview_id>/report")
@login_required
def report(interview_id):
    """Detailed web performance report page."""
    interview = db.session.get(Interview, interview_id)
    if not interview:
        abort(404)

    if interview.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    result = interview.result
    responses = interview.responses.all()
    proctoring_logs = interview.proctoring_logs.all()

    return render_template(
        "results.html",
        interview=interview,
        result=result,
        responses=responses,
        proctoring_logs=proctoring_logs,
        is_report_view=True,
    )


@interview_bp.route("/resume_setup", methods=["GET", "POST"])
@login_required
def resume_setup():
    """Resume upload page: candidates upload their CV to get personalized AI interview questions."""
    if request.method == "POST":
        # --- Validate uploaded file ---
        if "resume" not in request.files:
            flash("No resume file was selected. Please upload a PDF, DOCX, or TXT file.", "warning")
            return redirect(url_for("interview.resume_setup"))

        resume_file = request.files["resume"]
        if not resume_file or resume_file.filename == "":
            flash("No file selected. Please choose a resume file.", "warning")
            return redirect(url_for("interview.resume_setup"))

        filename = resume_file.filename
        allowed_extensions = {".pdf", ".docx", ".txt", ".doc"}
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            flash(f"Unsupported file type '{ext}'. Please upload a PDF, DOCX, or TXT file.", "danger")
            return redirect(url_for("interview.resume_setup"))

        file_bytes = resume_file.read()
        # 5 MB size limit
        if len(file_bytes) > 5 * 1024 * 1024:
            flash("Resume file size exceeds 5 MB limit. Please upload a smaller file.", "danger")
            return redirect(url_for("interview.resume_setup"))

        # --- Extract text from resume ---
        try:
            resume_text = ResumeService.extract_text_from_file(filename, file_bytes)
        except Exception as e:
            current_app.logger.error(f"Resume text extraction failed: {e}", exc_info=True)
            flash("Could not read the resume file. Please try a different format.", "danger")
            return redirect(url_for("interview.resume_setup"))

        if len(resume_text.strip()) < 30:
            flash("The uploaded resume appears to be empty or unreadable. Please try a text-based PDF or DOCX.", "warning")
            return redirect(url_for("interview.resume_setup"))

        # --- Parse form options ---
        try:
            question_count = int(request.form.get("question_count", 5))
            if question_count not in (5, 10, 15):
                question_count = 5
        except (ValueError, TypeError):
            question_count = 5

        difficulty = request.form.get("difficulty", "Medium")
        if difficulty not in ("Easy", "Medium", "Hard"):
            difficulty = "Medium"

        input_mode = request.form.get("input_mode", "text")
        if input_mode not in ("text", "voice"):
            input_mode = "text"

        # --- Generate questions using AI or rule-based fallback ---
        mode = current_app.config.get("EVALUATION_MODE", "auto").lower()
        use_ai = mode in ("ai", "auto") and not current_app.config.get("TESTING", False)
        api_key = current_app.config.get("GEMINI_API_KEY", "") if use_ai else ""
        try:
            generated_q_dicts = ResumeService.generate_resume_questions(
                resume_text,
                count=question_count,
                difficulty=difficulty,
                api_key=api_key,
            )
        except Exception as e:
            current_app.logger.error(f"Resume question generation failed: {e}", exc_info=True)
            flash("Question generation failed. Using general interview questions as fallback.", "warning")
            generated_q_dicts = ResumeService._generate_rule_based(resume_text, [], question_count, difficulty)

        if not generated_q_dicts:
            flash("Could not generate interview questions from your resume. Please try a more detailed resume.", "warning")
            return redirect(url_for("interview.resume_setup"))

        # --- Persist generated questions to DB ---
        persisted_questions = []
        for q_data in generated_q_dicts:
            question = Question(
                category="Technical",
                topic=q_data.get("topic", "Resume: General"),
                difficulty=q_data.get("difficulty", difficulty),
                question_text=q_data.get("question_text", ""),
                reference_answer=q_data.get("reference_answer", ""),
                keywords=q_data.get("keywords", ""),
                is_generated=True,
            )
            db.session.add(question)
            persisted_questions.append(question)

        db.session.flush()  # Assign IDs without committing yet

        # --- Create Interview session ---
        interview = Interview(
            user_id=current_user.id,
            category="Technical",
            topic="Resume-Based Interview",
            difficulty=difficulty,
            question_count=len(persisted_questions),
            input_mode=input_mode,
            status="in_progress",
            started_at=datetime.utcnow(),
            resume_text=resume_text[:5000],      # Store first 5000 chars for audit
            resume_filename=filename,
        )
        interview.question_ids = [q.id for q in persisted_questions]
        db.session.add(interview)
        db.session.commit()

        detected_skills = ResumeService.extract_skills(resume_text)
        skill_summary = ", ".join(detected_skills[:6]) if detected_skills else "General Software Engineering"
        flash(
            f"Resume analysed! Detected skills: {skill_summary}. "
            f"{len(persisted_questions)} personalised questions generated. Good luck!",
            "success",
        )
        return redirect(url_for("interview.live", interview_id=interview.id))

    # GET — render upload form
    return render_template("resume_setup.html")


@interview_bp.route("/<int:interview_id>/pdf")
@login_required
def download_pdf(interview_id):
    """Download comprehensive interview report as a PDF."""
    interview = Interview.query.get_or_404(interview_id)

    if interview.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    pdf_buffer = ReportService.generate_interview_pdf(interview)
    filename = f"AI_Interview_Report_{interview.id}_{interview.category}.pdf"

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
