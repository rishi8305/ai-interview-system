import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


class ReportService:
    """Service to generate professional, publication-quality PDF interview reports using ReportLab."""

    @classmethod
    def generate_interview_pdf(cls, interview) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        primary_color = colors.HexColor("#1e1b4b")  # Dark Indigo
        accent_color = colors.HexColor("#4f46e5")   # Indigo
        brand_blue = colors.HexColor("#2563eb")     # Royal Blue
        dark_text = colors.HexColor("#0f172a")      # Slate 900
        muted_text = colors.HexColor("#475569")     # Slate 600
        bg_light = colors.HexColor("#f8fafc")       # Slate 50
        border_color = colors.HexColor("#cbd5e1")   # Slate 300

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=primary_color,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            textColor=muted_text,
            fontName="Helvetica",
            alignment=TA_LEFT,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=accent_color,
            fontName="Helvetica-Bold",
            spaceBefore=12,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13.5,
            textColor=dark_text,
            fontName="Helvetica",
        )

        body_bold = ParagraphStyle(
            "BodyBold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )

        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#4338ca"),
            fontName="Helvetica-Bold",
        )

        center_score = ParagraphStyle(
            "CenterScore",
            parent=styles["Normal"],
            fontSize=24,
            leading=28,
            textColor=accent_color,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )

        elements = []

        # --- HEADER SECTION ---
        header_table = Table(
            [
                [
                    Paragraph("AI INTERVIEW ASSESSMENT REPORT", title_style),
                    Paragraph(
                        f"<b>Generated:</b> {datetime.utcnow().strftime('%B %d, %Y')}<br/>"
                        f"<b>Session ID:</b> #{interview.id}",
                        ParagraphStyle("MetaRight", parent=styles["Normal"], fontSize=8.5, leading=12, alignment=TA_RIGHT, textColor=muted_text),
                    ),
                ]
            ],
            colWidths=[350, 182],
        )
        header_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(header_table)

        elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceBefore=4, spaceAfter=14))

        # --- CANDIDATE & SESSION SUMMARY CARD ---
        user = interview.candidate
        result = interview.result

        percentage = result.percentage if result else (interview.total_score * 10.0 if interview.total_score else 0.0)
        overall_score = result.total_score if result else (interview.total_score or 0.0)

        meta_data = [
            [
                Paragraph("<b>Candidate Name:</b>", body_style),
                Paragraph(user.name if user else "Candidate", body_style),
                Paragraph("<b>Interview Category:</b>", body_style),
                Paragraph(f"{interview.category} - {interview.topic or 'General'}", body_style),
            ],
            [
                Paragraph("<b>Email:</b>", body_style),
                Paragraph(user.email if user else "N/A", body_style),
                Paragraph("<b>Difficulty Level:</b>", body_style),
                Paragraph(interview.difficulty, body_style),
            ],
            [
                Paragraph("<b>Interview Date:</b>", body_style),
                Paragraph(interview.started_at.strftime("%Y-%m-%d %H:%M") if interview.started_at else "N/A", body_style),
                Paragraph("<b>Input Mode:</b>", body_style),
                Paragraph(interview.input_mode.capitalize(), body_style),
            ],
            [
                Paragraph("<b>Evaluation Engine:</b>", body_style),
                Paragraph(interview.evaluation_mode, badge_style),
                Paragraph("<b>Total Questions:</b>", body_style),
                Paragraph(str(interview.responses.count()), body_style),
            ],
        ]

        meta_table = Table(meta_data, colWidths=[110, 160, 120, 142])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 12))

        # --- OVERALL PERFORMANCE SCORECARD ---
        elements.append(Paragraph("Overall Performance Scorecard", section_heading))

        score_color = colors.HexColor("#10b981") if percentage >= 75 else (colors.HexColor("#f59e0b") if percentage >= 50 else colors.HexColor("#ef4444"))
        status_label = "EXCELLENT / READY" if percentage >= 80 else ("GOOD / COMPETENT" if percentage >= 65 else "NEEDS PRACTICE")

        score_card_data = [
            [
                Paragraph(f"<b>Final Net Score</b><br/><font color='{score_color.hexval()}'>{overall_score:.1f}</font>/10", center_score),
                Paragraph(f"<b>Percentage</b><br/><font color='{score_color.hexval()}'>{percentage:.1f}%</font>", center_score),
                Paragraph(f"<b>Integrity Rating</b><br/><font size='16' color='#4338ca'><b>{interview.integrity_score:.0f}%</b></font>", center_score),
            ]
        ]
        score_card_table = Table(score_card_data, colWidths=[177, 177, 178])
        score_card_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        elements.append(score_card_table)
        elements.append(Spacer(1, 10))

        # --- PROCTORING & INTEGRITY SUMMARY ---
        elements.append(Paragraph("AI Proctoring & Session Integrity Verification", section_heading))
        raw_pct = (interview.raw_score * 10.0) if interview.raw_score else percentage
        tab_pen_pct = (interview.proctoring_penalty * 10.0) if interview.proctoring_penalty else 0.0

        proctor_data = [
            [
                Paragraph("<b>Monitored Integrity Metric</b>", body_bold),
                Paragraph("<b>Audit Finding</b>", body_bold),
                Paragraph("<b>Score Adjustment</b>", body_bold),
            ],
            [
                Paragraph("Browser Tab Switches", body_style),
                Paragraph(f"{interview.tab_switch_count} occurrence(s) recorded", body_style),
                Paragraph(f"<font color='#dc2626'><b>-{interview.tab_switch_count * 5}%</b></font>" if interview.tab_switch_count else "None (0%)", body_style),
            ],
            [
                Paragraph("Frame & Object Violations", body_style),
                Paragraph(f"{interview.violations_count} detected (multiple persons / objects)", body_style),
                Paragraph(f"<font color='#dc2626'><b>-{interview.violations_count * 5}%</b></font>" if interview.violations_count else "None (0%)", body_style),
            ],
            [
                Paragraph("Score Computation Audit", body_style),
                Paragraph(f"Raw AI Score: {interview.raw_score:.1f}/10 ({raw_pct:.1f}%)", body_style),
                Paragraph(f"<b>Net Final Score: {overall_score:.1f}/10 ({percentage:.1f}%)</b>", body_style),
            ],
        ]
        proctor_table = Table(proctor_data, colWidths=[180, 202, 150])
        proctor_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        elements.append(proctor_table)
        elements.append(Spacer(1, 10))

        # --- RUBRIC BREAKDOWN TABLE ---
        if result:
            rubric_data = [
                [
                    Paragraph("<b>Evaluation Criterion</b>", body_bold),
                    Paragraph("<b>Weight</b>", body_bold),
                    Paragraph("<b>Average Score (0-10)</b>", body_bold),
                    Paragraph("<b>Criterion Benchmark</b>", body_bold),
                ],
                [
                    Paragraph("Technical Correctness", body_style),
                    Paragraph("40%", body_style),
                    Paragraph(f"<b>{result.correctness_avg:.1f} / 10</b>", body_style),
                    Paragraph("Accurate definitions, logic & syntax", body_style),
                ],
                [
                    Paragraph("Relevance to Question", body_style),
                    Paragraph("25%", body_style),
                    Paragraph(f"<b>{result.relevance_avg:.1f} / 10</b>", body_style),
                    Paragraph("Direct alignment with prompt requirements", body_style),
                ],
                [
                    Paragraph("Completeness & Depth", body_style),
                    Paragraph("20%", body_style),
                    Paragraph(f"<b>{result.completeness_avg:.1f} / 10</b>", body_style),
                    Paragraph("Thorough coverage of edge cases and examples", body_style),
                ],
                [
                    Paragraph("Clarity & Communication", body_style),
                    Paragraph("15%", body_style),
                    Paragraph(f"<b>{result.clarity_avg:.1f} / 10</b>", body_style),
                    Paragraph("Structured articulation and concise phrasing", body_style),
                ],
            ]
            rubric_table = Table(rubric_data, colWidths=[150, 70, 130, 182])
            rubric_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("BOX", (0, 0), (-1, -1), 1, border_color),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ])
            )
            elements.append(rubric_table)
            elements.append(Spacer(1, 10))

        # --- STRENGTHS & RECOMMENDATIONS ---
        if result and (result.strengths or result.recommendations):
            elements.append(Paragraph("Key Strengths & Recommendations", section_heading))
            feedback_items = []
            if result.strengths:
                feedback_items.append([Paragraph("<b>Demonstrated Strengths:</b>", body_bold)])
                for s in result.strengths:
                    feedback_items.append([Paragraph(f"&bull; {s}", body_style)])
            if result.recommendations:
                feedback_items.append([Paragraph("<b>Actionable Recommendations:</b>", body_bold)])
                for r in result.recommendations:
                    feedback_items.append([Paragraph(f"&bull; {r}", body_style)])

            feedback_table = Table(feedback_items, colWidths=[532])
            feedback_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                    ("BOX", (0, 0), (-1, -1), 1, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ])
            )
            elements.append(feedback_table)
            elements.append(Spacer(1, 12))

        # --- DETAILED QUESTION-WISE RESPONSES ---
        elements.append(Paragraph("Detailed Question Breakdown", section_heading))

        responses = interview.responses.all()
        for idx, resp in enumerate(responses, start=1):
            q = resp.question
            q_text = q.question_text if q else "Question text not available"

            q_data = [
                [
                    Paragraph(f"<b>Question {idx} of {len(responses)}:</b> {q_text}", body_bold),
                    Paragraph(f"<b>Score: {resp.overall_score:.1f}/10</b>", ParagraphStyle("QScore", parent=body_bold, textColor=accent_color, alignment=TA_RIGHT)),
                ],
                [
                    Paragraph(
                        f"<b>Candidate Answer:</b><br/>{resp.answer_text if resp.answer_text else '<i>No answer provided</i>'}",
                        body_style,
                    ),
                    Paragraph(
                        f"Correctness: {resp.correctness_score:.1f}/10<br/>"
                        f"Relevance: {resp.relevance_score:.1f}/10<br/>"
                        f"Completeness: {resp.completeness_score:.1f}/10<br/>"
                        f"Clarity: {resp.clarity_score:.1f}/10",
                        ParagraphStyle("ScoresMini", parent=styles["Normal"], fontSize=8, leading=11, textColor=muted_text),
                    ),
                ],
                [
                    Paragraph(
                        f"<b>AI Evaluator Feedback:</b> {resp.feedback}<br/>"
                        f"<b>Ideal Reference Answer:</b> {resp.suggested_answer or (q.reference_answer if q else 'N/A')}",
                        ParagraphStyle("FeedStyle", parent=body_style, fontSize=8.5, leading=12),
                    ),
                    "",
                ],
            ]

            q_table = Table(q_data, colWidths=[420, 112])
            q_table.setStyle(
                TableStyle([
                    ("SPAN", (0, 2), (1, 2)),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, border_color),
                    ("LINEBELOW", (0, 1), (-1, 1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )

            elements.append(KeepTogether([q_table, Spacer(1, 8)]))

        # --- FOOTER NOTE ---
        elements.append(Spacer(1, 10))
        elements.append(
            Paragraph(
                "This assessment was generated automatically by the AI Interview System. "
                "Scores and feedback are evaluated strictly based on communication and technical rubrics without bias.",
                ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=muted_text, alignment=TA_CENTER),
            )
        )

        doc.build(elements)
        buffer.seek(0)
        return buffer
