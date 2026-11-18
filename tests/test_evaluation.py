from services import EvaluationService, AIService
from models import Question


def test_rubric_weights_calculation():
    """Verify that rubric weights exactly equal 40% correctness, 25% relevance, 20% completeness, 15% clarity."""
    sample_data = {
        "correctness": 10.0,
        "relevance": 8.0,
        "completeness": 6.0,
        "clarity": 9.0,
        "strengths": ["Clear explanation"],
        "weaknesses": ["Minor edge cases"],
        "feedback": "Great response",
        "suggested_answer": "Model answer",
        "improvement_tips": ["Keep practicing"],
    }
    normalized = AIService._validate_and_normalize_evaluation(sample_data)

    # 10*0.40 + 8*0.25 + 6*0.20 + 9*0.15 = 4.0 + 2.0 + 1.2 + 1.35 = 8.55 -> rounded to 8.6
    expected_score = round((10.0 * 0.40) + (8.0 * 0.25) + (6.0 * 0.20) + (9.0 * 0.15), 1)
    assert normalized["overall_score"] == expected_score
    assert normalized["correctness"] == 10.0
    assert normalized["relevance"] == 8.0
    assert normalized["completeness"] == 6.0
    assert normalized["clarity"] == 9.0


def test_rubric_clamping_bounds():
    """Verify out-of-range scores are clamped between 0.0 and 10.0."""
    out_of_bounds = {
        "correctness": 99.0,
        "relevance": -5.0,
        "completeness": 12.0,
        "clarity": -1.0,
    }
    normalized = AIService._validate_and_normalize_evaluation(out_of_bounds)
    assert normalized["correctness"] == 10.0
    assert normalized["relevance"] == 0.0
    assert normalized["completeness"] == 10.0
    assert normalized["clarity"] == 0.0


def test_rule_based_evaluator_keywords(app):
    """Test rule-based evaluator identifies keywords and reference tokens."""
    with app.app_context():
        q = Question.query.filter_by(topic="Python", difficulty="Easy").first()
        good_answer = "A list comprehension is a concise and readable way to create a new list from an iterable using square bracket syntax."
        eval_result, label = EvaluationService.evaluate(q, good_answer)

        assert eval_result["overall_score"] >= 5.0
        assert eval_result["correctness"] >= 5.0
        assert eval_result["relevance"] >= 5.0
        assert "Rule-Based" in label or "AI" in label
        assert len(eval_result["strengths"]) > 0
        assert len(eval_result["feedback"]) > 0


def test_empty_answer_handling(app):
    """Test submitting empty answer receives 0 score gracefully without crashing."""
    with app.app_context():
        q = Question.query.first()
        eval_result, label = EvaluationService.evaluate(q, "")
        assert eval_result["overall_score"] == 0.0
        assert eval_result["correctness"] == 0.0
        assert eval_result["relevance"] == 0.0
        assert eval_result["completeness"] == 0.0
        assert eval_result["clarity"] == 0.0
        assert "No answer was submitted" in eval_result["feedback"]
