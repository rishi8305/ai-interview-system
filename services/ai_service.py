import os
import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


RUBRIC_PROMPT_TEMPLATE = """You are an expert technical interviewer and hiring assessment specialist.
Evaluate the following candidate response to the interview question using the specified rubric.

### QUESTION DETAILS:
- Category: {category}
- Topic: {topic}
- Difficulty: {difficulty}
- Question: {question}
- Reference Answer / Key Concepts: {reference_answer}
- Expected Keywords: {keywords}

### CANDIDATE'S SUBMITTED ANSWER:
"{candidate_answer}"

### EVALUATION CRITERIA (Score each from 0.0 to 10.0):
1. Technical Correctness (40% weight): Accuracy of facts, technical definitions, syntax/logic, concepts.
2. Relevance (25% weight): How directly and accurately the answer addresses the question asked.
3. Completeness (20% weight): Coverage of essential points, edge cases, and necessary depth for {difficulty} level.
4. Clarity (15% weight): Communication quality, structure, articulation, and concise explanation.

### STRICT OUTPUT FORMAT:
You MUST respond ONLY with a single valid JSON object. Do not include markdown code blocks, backticks, or conversational preamble.
The JSON must follow this exact schema:
{{
  "correctness": <float 0.0-10.0>,
  "relevance": <float 0.0-10.0>,
  "completeness": <float 0.0-10.0>,
  "clarity": <float 0.0-10.0>,
  "overall_score": <float 0.0-10.0>,
  "strengths": ["<specific strength 1>", "<specific strength 2>"],
  "weaknesses": ["<specific weakness or gap 1>", "<specific weakness or gap 2>"],
  "feedback": "<concise constructive feedback paragraph directly addressing the candidate>",
  "suggested_answer": "<ideal, high-scoring model answer for this interview question>",
  "improvement_tips": ["<actionable advice 1>", "<actionable advice 2>"]
}}
"""


class AIService:
    """Service to interact with Google Gemini or OpenAI APIs for interview response evaluation."""

    @staticmethod
    def _clean_json_response(raw_text: str) -> str:
        """Strip markdown fences and whitespace from raw LLM output."""
        text = raw_text.strip()
        # Remove ```json and ``` fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        # Find outer JSON object if extra text exists
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return text

    @classmethod
    def _validate_and_normalize_evaluation(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all fields conform to schema and bounds."""
        def clamp(val, low=0.0, high=10.0):
            try:
                v = float(val)
                return max(low, min(high, round(v, 1)))
            except (ValueError, TypeError):
                return 5.0

        correctness = clamp(data.get("correctness", 5.0))
        relevance = clamp(data.get("relevance", 5.0))
        completeness = clamp(data.get("completeness", 5.0))
        clarity = clamp(data.get("clarity", 5.0))

        # Mathematically calculate weighted overall score (40% + 25% + 20% + 15%)
        computed_overall = round(
            (correctness * 0.40) +
            (relevance * 0.25) +
            (completeness * 0.20) +
            (clarity * 0.15),
            1
        )

        strengths = data.get("strengths")
        if not isinstance(strengths, list) or not strengths:
            strengths = ["Identified key concepts relevant to the question."]
        else:
            strengths = [str(s).strip() for s in strengths if str(s).strip()]

        weaknesses = data.get("weaknesses")
        if not isinstance(weaknesses, list) or not weaknesses:
            weaknesses = ["Could provide more technical depth and examples."]
        else:
            weaknesses = [str(w).strip() for w in weaknesses if str(w).strip()]

        improvement_tips = data.get("improvement_tips")
        if not isinstance(improvement_tips, list) or not improvement_tips:
            improvement_tips = ["Practice explaining core trade-offs and real-world use cases."]
        else:
            improvement_tips = [str(t).strip() for t in improvement_tips if str(t).strip()]

        return {
            "correctness": correctness,
            "relevance": relevance,
            "completeness": completeness,
            "clarity": clarity,
            "overall_score": computed_overall,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "feedback": str(data.get("feedback", "Good effort. Review suggested answer for full coverage.")).strip(),
            "suggested_answer": str(data.get("suggested_answer", "Refer to the standard documentation and best practices.")).strip(),
            "improvement_tips": improvement_tips,
        }

    @classmethod
    def evaluate_with_gemini(
        cls,
        api_key: str,
        model_name: str,
        question_data: Dict[str, Any],
        candidate_answer: str,
    ) -> Dict[str, Any]:
        """Evaluate candidate response using Google Gemini API."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name or "gemini-1.5-flash")

            prompt = RUBRIC_PROMPT_TEMPLATE.format(
                category=question_data.get("category", "General"),
                topic=question_data.get("topic", "General"),
                difficulty=question_data.get("difficulty", "Medium"),
                question=question_data.get("question_text", ""),
                reference_answer=question_data.get("reference_answer", "None provided"),
                keywords=question_data.get("keywords", "None"),
                candidate_answer=candidate_answer,
            )

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json" if "1.5" in (model_name or "") else None,
                ),
            )

            raw_text = response.text or ""
            cleaned = cls._clean_json_response(raw_text)
            parsed = json.loads(cleaned)
            return cls._validate_and_normalize_evaluation(parsed)
        except Exception as e:
            logger.error(f"Gemini API evaluation failed: {e}", exc_info=True)
            raise RuntimeError(f"Gemini API error: {str(e)}")

    @classmethod
    def evaluate_with_openai(
        cls,
        api_key: str,
        model_name: str,
        question_data: Dict[str, Any],
        candidate_answer: str,
    ) -> Dict[str, Any]:
        """Evaluate candidate response using OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            prompt = RUBRIC_PROMPT_TEMPLATE.format(
                category=question_data.get("category", "General"),
                topic=question_data.get("topic", "General"),
                difficulty=question_data.get("difficulty", "Medium"),
                question=question_data.get("question_text", ""),
                reference_answer=question_data.get("reference_answer", "None provided"),
                keywords=question_data.get("keywords", "None"),
                candidate_answer=candidate_answer,
            )

            response = client.chat.completions.create(
                model=model_name or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional technical interview evaluator. You return only valid JSON according to the schema requested."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            raw_text = response.choices[0].message.content or ""
            cleaned = cls._clean_json_response(raw_text)
            parsed = json.loads(cleaned)
            return cls._validate_and_normalize_evaluation(parsed)
        except Exception as e:
            logger.error(f"OpenAI API evaluation failed: {e}", exc_info=True)
            raise RuntimeError(f"OpenAI API error: {str(e)}")
