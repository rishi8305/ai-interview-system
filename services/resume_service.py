import io
import re
import json
import zlib
import zipfile
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

COMMON_SKILLS = [
    "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "React", "Angular", "Vue",
    "Node.js", "Express", "Flask", "Django", "FastAPI", "Spring Boot", "HTML", "CSS", "Bootstrap",
    "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Oracle",
    "Machine Learning", "Deep Learning", "Artificial Intelligence", "NLP", "Computer Vision",
    "TensorFlow", "PyTorch", "Keras", "Scikit-Learn", "Pandas", "NumPy",
    "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "CI/CD", "Git", "GitHub", "Linux",
    "Data Structures", "Algorithms", "System Design", "Microservices", "REST API", "GraphQL"
]


class ResumeService:
    """Service to parse candidate resumes and generate customized interview questions."""

    @classmethod
    def extract_text_from_file(cls, filename: str, file_bytes: bytes) -> str:
        """Extract plain text from uploaded PDF, DOCX, or TXT file."""
        lower_name = (filename or "").lower()

        try:
            if lower_name.endswith(".docx"):
                return cls._extract_from_docx(file_bytes)
            elif lower_name.endswith(".pdf"):
                return cls._extract_from_pdf(file_bytes)
            else:
                # Text / Markdown / RTF fallback
                try:
                    return file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    return file_bytes.decode("latin-1", errors="ignore")
        except Exception as e:
            logger.error(f"Error parsing resume file {filename}: {e}", exc_info=True)
            # Try plain string decode as last resort
            return file_bytes.decode("utf-8", errors="ignore")

    @classmethod
    def _extract_from_docx(cls, file_bytes: bytes) -> str:
        """Extract text from DOCX archive word/document.xml without external libraries."""
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            texts = [node.text for node in tree.iter() if node.text]
            return " ".join(texts)

    @classmethod
    def _extract_from_pdf(cls, file_bytes: bytes) -> str:
        """Extract text from PDF streams using zlib and regex stream decoding."""
        text_chunks = []
        pattern = re.compile(b"stream[\r\n]+(.*?)[\r\n]+endstream", re.DOTALL)

        for match in pattern.finditer(file_bytes):
            stream_data = match.group(1)
            decompressed = None
            try:
                decompressed = zlib.decompress(stream_data)
            except Exception:
                try:
                    decompressed = zlib.decompress(stream_data, -zlib.MAX_WBITS)
                except Exception:
                    decompressed = stream_data

            if decompressed:
                # Extract text chunks enclosed in parentheses e.g. (text) Tj
                strings = re.findall(b"\((.*?)\)", decompressed)
                for s in strings:
                    try:
                        decoded = s.decode("latin1", errors="ignore")
                        if len(decoded.strip()) > 1 and any(c.isalnum() for c in decoded):
                            text_chunks.append(decoded.strip())
                    except Exception:
                        pass

        # Also search for plain text ASCII matches in raw binary
        plain_matches = re.findall(b"\(([a-zA-Z0-9 .,_/-]{3,})\)", file_bytes)
        for pm in plain_matches:
            try:
                text_chunks.append(pm.decode("utf-8", errors="ignore"))
            except Exception:
                pass

        extracted = " ".join(dict.fromkeys(text_chunks))
        if len(extracted.strip()) < 20:
            # Fallback regex for ASCII text blocks
            words = re.findall(r"[A-Za-z0-9][A-Za-z0-9 .,;:_/-]{4,}", file_bytes.decode("latin1", errors="ignore"))
            extracted = " ".join(words[:400])

        return extracted

    @classmethod
    def extract_skills(cls, resume_text: str) -> List[str]:
        """Identify matched technical skills mentioned in the resume text."""
        matched = []
        text_lower = (resume_text or "").lower()
        for skill in COMMON_SKILLS:
            # Word boundary matching
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched.append(skill)
        return matched

    @classmethod
    def generate_resume_questions(
        cls,
        resume_text: str,
        count: int = 5,
        difficulty: str = "Medium",
        api_key: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Generate customized interview questions tailored to the candidate's resume.
        Uses Google Gemini AI if API key is provided, with intelligent template fallback.
        """
        clean_text = (resume_text or "").strip()
        skills = cls.extract_skills(clean_text)

        # 1. Try Gemini AI Generation if key is available
        if api_key and len(clean_text) > 20:
            try:
                return cls._generate_with_gemini(clean_text, skills, count, difficulty, api_key)
            except Exception as e:
                logger.warning(f"Gemini resume question generation failed: {e}. Falling back to tailored template engine.")

        # 2. Intelligent Template Fallback based on extracted resume skills
        return cls._generate_rule_based(clean_text, skills, count, difficulty)

    @classmethod
    def _generate_with_gemini(
        cls, resume_text: str, skills: List[str], count: int, difficulty: str, api_key: str
    ) -> List[Dict[str, Any]]:
        """Generate targeted resume interview questions via Gemini API."""
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""You are a senior technical hiring manager and interviewer.
Analyze the following candidate resume text and detected skills:
Detected Skills: {', '.join(skills) if skills else 'Software Engineering'}

CANDIDATE RESUME EXCERPT:
\"\"\"{resume_text[:2500]}\"\"\"

Generate exactly {count} interview questions at {difficulty} difficulty tailored directly to this candidate's listed projects, technologies, and technical experience.
Each question should probe real practical implementations, architecture decisions, trade-offs, or challenges related to what they wrote.

Return ONLY a valid JSON list of objects with this exact schema:
[
  {{
    "question_text": "<In-depth interview question referencing their specific resume skill or project>",
    "topic": "<Relevant Skill or Topic from resume>",
    "difficulty": "{difficulty}",
    "reference_answer": "<Comprehensive ideal model answer explaining what a strong candidate should cover>",
    "keywords": "<comma-separated key technical terms expected in candidate response>"
  }}
]
"""
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.3, response_mime_type="application/json"),
        )
        raw_text = response.text or ""
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        parsed = json.loads(cleaned)

        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed[:count]
        raise ValueError("Invalid format returned by Gemini")

    @classmethod
    def _generate_rule_based(
        cls, resume_text: str, skills: List[str], count: int, difficulty: str
    ) -> List[Dict[str, Any]]:
        """Synthesize personalized questions based on extracted resume skills and projects."""
        templates = [
            {
                "skill": "Python",
                "question": "Your resume highlights Python experience. Can you explain how you handle memory management, decorators, or multithreading/multiprocessing in a production Python application?",
                "reference": "Candidate should discuss CPython reference counting, garbage collection cycles, GIL constraints, and when to use multiprocessing vs asyncio.",
                "keywords": "CPython, memory, garbage collection, GIL, asyncio, multiprocessing, generator",
            },
            {
                "skill": "Java",
                "question": "Based on your Java background listed on your resume, how do you ensure thread safety when sharing data between concurrent threads, and what is your experience with the Java Memory Model?",
                "reference": "Candidate should cover synchronization, volatile variables, atomic variables, ConcurrentHashMap, and Heap vs Stack memory divisions.",
                "keywords": "synchronization, volatile, atomic, thread safety, concurrenthashmap, heap, stack",
            },
            {
                "skill": "SQL",
                "question": "In your resume, you mention relational databases and SQL. Can you describe how you optimize slow queries, design indexes, and resolve N+1 query problems?",
                "reference": "Explain EXPLAIN query execution plans, B-Tree indexing trade-offs, composite indexes, query refactoring, and eager loading.",
                "keywords": "indexing, execution plan, explain, join optimization, b-tree, normalization",
            },
            {
                "skill": "Machine Learning",
                "question": "Your resume includes Machine Learning projects. Can you walk me through your pipeline: data preprocessing, handling class imbalance, feature selection, and validation methodology?",
                "reference": "Candidate should detail cross-validation (K-fold), SMOTE or class weighting for imbalance, metrics like ROC-AUC / F1-Score, and avoiding data leakage.",
                "keywords": "cross validation, feature engineering, class imbalance, f1 score, precision, recall, leakage",
            },
            {
                "skill": "React",
                "question": "You listed React on your resume. How do you manage global state, optimize re-renders using hooks like useMemo/useCallback, and handle asynchronous data fetching?",
                "reference": "Candidate should explain the Virtual DOM, reconciliation, useEffect cleanups, memoization trade-offs, and state management like Context API or Redux.",
                "keywords": "virtual dom, hooks, usememo, usecallback, state management, reconciliation",
            },
            {
                "skill": "Docker",
                "question": "Your resume indicates DevOps and Docker knowledge. How do you construct multi-stage Docker builds to minimize image sizes, and how do you manage container networking?",
                "reference": "Discuss multi-stage Dockerfiles separating build and runtime environments, volume mounts, bridge networks, and security best practices.",
                "keywords": "multi-stage build, dockerfile, container, image size, bridge network, volumes",
            },
            {
                "skill": "REST API",
                "question": "You have listed REST API / Web Development on your resume. How do you design idempotent endpoints, structure authentication (JWT vs Sessions), and handle rate limiting?",
                "reference": "Discuss HTTP methods idempotency (GET/PUT/DELETE vs POST), JWT token expiration, refresh tokens, status codes, and rate limiting algorithms.",
                "keywords": "idempotent, REST, JWT, authentication, status codes, rate limiting, stateless",
            },
            {
                "skill": "General",
                "question": "Can you walk me through the system architecture of the most technically challenging project on your resume? What key trade-offs did you evaluate?",
                "reference": "Candidate should clearly outline the problem statement, high-level architecture, database choice, API design, scalability bottlenecks, and lessons learned.",
                "keywords": "architecture, trade-offs, scalability, database, microservices, performance",
            },
            {
                "skill": "General",
                "question": "Looking at the project experience on your resume, describe a major technical bug or performance bottleneck you encountered. How did you diagnose and resolve it?",
                "reference": "Use the STAR method: Describe the bug symptoms, profiling/debugging tools used, root cause analysis, fix implemented, and tests added to prevent recurrence.",
                "keywords": "debugging, root cause, profiling, testing, bottleneck, optimization",
            },
            {
                "skill": "General",
                "question": "How did you approach automated testing and continuous integration (CI/CD) in the projects documented on your resume?",
                "reference": "Explain unit testing, integration tests, mock objects, CI pipelines (GitHub Actions, Jenkins), code coverage, and automated deployment.",
                "keywords": "unit testing, integration testing, CI/CD, github actions, mocks, code coverage",
            },
        ]

        matched_questions = []

        # Find questions matching the candidate's actual skills
        for s in skills:
            for t in templates:
                if t["skill"].lower() == s.lower() and t not in matched_questions:
                    matched_questions.append(t)

        # Supplement with general project architectural questions
        for t in templates:
            if t["skill"] == "General" and t not in matched_questions:
                matched_questions.append(t)

        selected = matched_questions[:count]

        # Convert to standard question format
        results = []
        for q in selected:
            results.append({
                "question_text": q["question"],
                "topic": f"Resume: {q['skill']}",
                "difficulty": difficulty,
                "reference_answer": q["reference"],
                "keywords": q["keywords"],
            })

        return results
