import re
import string
import logging
from typing import Dict, Any, Tuple
from flask import current_app

from .ai_service import AIService
from models.question import Question

logger = logging.getLogger(__name__)


class EvaluationService:
    """Evaluation dispatcher supporting real AI (Gemini / OpenAI) and rule-based demo mode."""

    @classmethod
    def evaluate(cls, question: Question, candidate_answer: str) -> Tuple[Dict[str, Any], str]:
        """
        Evaluate candidate response.
        Returns: (evaluation_dict, evaluation_provider_label)
        """
        answer_clean = (candidate_answer or "").strip()
        if not answer_clean:
            return {
                "correctness": 0.0,
                "relevance": 0.0,
                "completeness": 0.0,
                "clarity": 0.0,
                "overall_score": 0.0,
                "strengths": ["None identified (No response was submitted)."],
                "weaknesses": ["Candidate did not provide an answer to this question."],
                "feedback": "No answer was submitted. In an interview, even a partial answer or honest admission is better than silence.",
                "suggested_answer": question.reference_answer or "Review the fundamental concepts for this topic.",
                "improvement_tips": ["Always attempt to share what you know, even if incomplete.", "Structure your thinking before speaking/typing."],
            }, "System Assessment (Empty Answer)"

        config = current_app.config
        mode = config.get("EVALUATION_MODE", "auto").lower()
        provider = config.get("AI_PROVIDER", "gemini").lower()
        gemini_key = config.get("GEMINI_API_KEY", "")
        openai_key = config.get("OPENAI_API_KEY", "")

        question_data = {
            "id": question.id,
            "category": question.category,
            "topic": question.topic or "General",
            "difficulty": question.difficulty,
            "question_text": question.question_text,
            "reference_answer": question.reference_answer or "",
            "keywords": question.keywords or "",
        }

        # Attempt Real AI Evaluation if configured
        if mode in ("ai", "auto"):
            if provider == "gemini" and gemini_key:
                try:
                    result = AIService.evaluate_with_gemini(
                        api_key=gemini_key,
                        model_name=config.get("GEMINI_MODEL", "gemini-1.5-flash"),
                        question_data=question_data,
                        candidate_answer=answer_clean,
                    )
                    return result, f"Google Gemini AI ({config.get('GEMINI_MODEL', 'gemini-1.5-flash')})"
                except Exception as e:
                    logger.warning(f"Gemini evaluation failed: {e}. Checking fallback.")
                    if mode == "ai":
                        raise RuntimeError(f"AI Service Failure: {str(e)}")

            elif provider == "openai" and openai_key:
                try:
                    result = AIService.evaluate_with_openai(
                        api_key=openai_key,
                        model_name=config.get("OPENAI_MODEL", "gpt-4o-mini"),
                        question_data=question_data,
                        candidate_answer=answer_clean,
                    )
                    return result, f"OpenAI GPT ({config.get('OPENAI_MODEL', 'gpt-4o-mini')})"
                except Exception as e:
                    logger.warning(f"OpenAI evaluation failed: {e}. Checking fallback.")
                    if mode == "ai":
                        raise RuntimeError(f"AI Service Failure: {str(e)}")

        # Fallback to clearly labeled Rule-Based Offline Evaluation
        rule_result = cls._evaluate_rule_based(question, answer_clean)
        return rule_result, "Rule-Based Offline Evaluator (Demo Mode)"

    @classmethod
    def _evaluate_rule_based(cls, question: Question, answer: str) -> Dict[str, Any]:
        """
        Rule-based NLP evaluator for development, offline demo, and verification.
        Uses keyword matching, semantic length, complexity indicators, and reference comparison.
        """
        words = re.findall(r"\b\w+\b", answer.lower())
        word_count = len(words)
        answer_lower = answer.lower()

        # Expected keywords check
        expected_keywords = []
        if question.keywords:
            expected_keywords = [k.strip().lower() for k in question.keywords.split(",") if k.strip()]

        # Reference answer key tokens (length > 3, exclude stop words)
        ref_tokens = []
        if question.reference_answer:
            tokens = re.findall(r"\b\w+\b", question.reference_answer.lower())
            stop_words = {"this", "that", "with", "from", "have", "were", "been", "which", "there", "their", "about", "would", "these"}
            ref_tokens = [t for t in tokens if len(t) > 3 and t not in stop_words]

        # Calculate keyword match ratio
        matched_keywords = [k for k in expected_keywords if k in answer_lower]
        keyword_score = (len(matched_keywords) / max(len(expected_keywords), 1)) if expected_keywords else 0.7

        # Reference token match
        matched_tokens = [t for t in set(ref_tokens) if t in answer_lower]
        token_score = (len(matched_tokens) / max(len(set(ref_tokens)), 1)) if ref_tokens else 0.6

        # Completeness based on depth and word count (ideal: 40-150 words depending on difficulty)
        target_words = {"Easy": 35, "Medium": 60, "Hard": 85}.get(question.difficulty, 50)
        length_ratio = min(word_count / target_words, 1.2)

        # Structure / clarity indicators (sentence count, punctuation, transition words)
        sentences = [s for s in re.split(r"[.!?]+", answer) if s.strip()]
        avg_sentence_len = word_count / max(len(sentences), 1)
        clarity_bonus = 0.5 if 8 <= avg_sentence_len <= 30 else -0.5
        transition_words = ["because", "therefore", "for example", "furthermore", "additionally", "such as", "however"]
        has_transition = any(t in answer_lower for t in transition_words)

        # Rubric Scores (0 to 10)
        correctness = min(10.0, max(2.0, (keyword_score * 5.0) + (token_score * 3.5) + (1.5 if word_count > 15 else 0.0)))
        relevance = min(10.0, max(2.5, (keyword_score * 6.0) + (token_score * 3.0) + (1.0 if any(k in answer_lower for k in expected_keywords) else 0.0)))
        completeness = min(10.0, max(1.5, length_ratio * 7.5 + (2.5 if len(matched_keywords) >= len(expected_keywords)//2 else 0.0)))
        clarity = min(10.0, max(3.0, (6.0 if len(sentences) >= 2 else 4.0) + (1.5 if has_transition else 0.0) + clarity_bonus + (1.5 if word_count >= 20 else 0.0)))

        # Round individual scores
        correctness = round(correctness, 1)
        relevance = round(relevance, 1)
        completeness = round(completeness, 1)
        clarity = round(clarity, 1)

        # Weighted calculation (40% correctness, 25% relevance, 20% completeness, 15% clarity)
        overall_score = round(
            (correctness * 0.40) +
            (relevance * 0.25) +
            (completeness * 0.20) +
            (clarity * 0.15),
            1
        )

        # Generate strengths & weaknesses
        strengths = []
        weaknesses = []
        improvement_tips = []

        if matched_keywords:
            strengths.append(f"Successfully integrated relevant industry terms: {', '.join(matched_keywords[:3])}.")
        if word_count >= target_words:
            strengths.append("Provided an adequate level of detail and explanation.")
        if has_transition:
            strengths.append("Structured the explanation logically with clear transitional flow.")
        if not strengths:
            strengths.append("Attempted the question directly with basic context.")

        if len(matched_keywords) < len(expected_keywords):
            missing = [k for k in expected_keywords if k not in matched_keywords]
            if missing:
                weaknesses.append(f"Omitted important related concepts: {', '.join(missing[:3])}.")
        if word_count < target_words * 0.6:
            weaknesses.append(f"Response was somewhat brief for a {question.difficulty} level interview question.")
        if len(sentences) <= 1:
            weaknesses.append("Response could benefit from separation into multiple well-structured sentences.")
        if not weaknesses:
            weaknesses.append("Minor room for deeper real-world optimization trade-offs.")

        # Practical tips
        improvement_tips.append("Use the STAR (Situation, Task, Action, Result) method for behavioral answers or clear concept-definition-example for technical answers.")
        if expected_keywords:
            improvement_tips.append(f"Incorporate industry standard terminology like {expected_keywords[0]} to reinforce credibility.")
        improvement_tips.append("Always state the 'why' behind an architectural choice or definition.")

        feedback = (
            f"Your response demonstrated good familiarity with {question.topic or question.category}. "
            f"You scored {overall_score}/10 based on technical accuracy ({correctness}/10) and relevance ({relevance}/10). "
            f"To achieve top percentiles, expand on concrete examples and boundary conditions."
        )

        return {
            "correctness": correctness,
            "relevance": relevance,
            "completeness": completeness,
            "clarity": clarity,
            "overall_score": overall_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "feedback": feedback,
            "suggested_answer": question.reference_answer or "Review documentation for standard reference answers.",
            "improvement_tips": improvement_tips,
        }

    @classmethod
    def aggregate_interview_result(cls, interview) -> Dict[str, Any]:
        """
        Aggregate individual question responses to produce the final comprehensive interview result.
        """
        responses = interview.responses.all()
        if not responses:
            return {
                "total_score": 0.0,
                "percentage": 0.0,
                "correctness_avg": 0.0,
                "relevance_avg": 0.0,
                "completeness_avg": 0.0,
                "clarity_avg": 0.0,
                "strengths": [],
                "weaknesses": [],
                "recommendations": ["Complete an interview to receive personalized recommendations."],
            }

        count = len(responses)
        total_overall = sum(r.overall_score for r in responses)
        avg_score = round(total_overall / count, 1)
        percentage = round((avg_score / 10.0) * 100, 1)

        corr_avg = round(sum(r.correctness_score for r in responses) / count, 1)
        rel_avg = round(sum(r.relevance_score for r in responses) / count, 1)
        comp_avg = round(sum(r.completeness_score for r in responses) / count, 1)
        clar_avg = round(sum(r.clarity_score for r in responses) / count, 1)

        # Aggregate unique strengths and weaknesses
        all_strengths = []
        for r in responses:
            all_strengths.extend(r.strengths)
        # Deduplicate while preserving order
        unique_strengths = list(dict.fromkeys(all_strengths))[:5]

        all_weaknesses = []
        for r in responses:
            all_weaknesses.extend(r.weaknesses)
        unique_weaknesses = list(dict.fromkeys(all_weaknesses))[:5]

        # Formulate tailored recommendations
        recommendations = []
        if corr_avg < 7.0:
            recommendations.append(f"Strengthen core foundational concepts in {interview.topic or interview.category}; revise standard definitions and syntax.")
        else:
            recommendations.append(f"Strong theoretical knowledge in {interview.topic or interview.category}. Continue with advanced system design and edge cases.")

        if comp_avg < 6.5:
            recommendations.append("Provide more comprehensive explanations with edge case handling, time/space complexities, or trade-offs.")
        if clar_avg < 7.0:
            recommendations.append("Structure answers clearly: begin with a direct definition, follow with the technical mechanism, and end with a concrete example.")
        if percentage >= 80.0:
            recommendations.append("Outstanding performance! You are well-prepared for real-world interviews at this difficulty level.")
        elif percentage >= 60.0:
            recommendations.append("Solid performance. Targeted practice on the identified weaknesses will elevate your score to top percentile.")
        else:
            recommendations.append("Further focused preparation recommended. Retake practice interviews to build confidence and vocabulary.")

        return {
            "total_score": avg_score,
            "percentage": percentage,
            "correctness_avg": corr_avg,
            "relevance_avg": rel_avg,
            "completeness_avg": comp_avg,
            "clarity_avg": clar_avg,
            "strengths": unique_strengths,
            "weaknesses": unique_weaknesses,
            "recommendations": recommendations,
        }
