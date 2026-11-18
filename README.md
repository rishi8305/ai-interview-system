# AI Interview System &mdash; Full-Stack AI Platform

An automated, enterprise-grade AI-powered interview platform developed as a B.Tech Computer Science minor project. The system conducts technical, HR, and aptitude interviews, evaluates candidate spoken and typed responses using Natural Language Processing and AI against an objective 4-part scoring rubric, calculates performance scores, generates interactive analytics, and produces downloadable PDF assessment reports.

---

## 1. Project Overview

- **Project Title:** AI Interview System
- **Purpose:** Help students and job seekers prepare for real-world interviews through realistic automated simulations with actionable AI-driven feedback.
- **Target Audience:** Job seekers, engineering students, college placement cells, and recruiters.
- **Evaluation Criteria (Strict Rubric):**
  - **Technical Correctness (40%)**: Accuracy of concepts, syntax, facts, and underlying logic.
  - **Relevance to Prompt (25%)**: Directness in addressing the specific question asked.
  - **Completeness & Depth (20%)**: Coverage of edge cases, architectural trade-offs, and detail.
  - **Clarity & Communication (15%)**: Articulation, structure, and coherent phrasing.

---

## 2. Key Features

- **Automated AI Interviews**: Real-time interactive session conducting one question at a time.
- **AI Face Configuration & Live Proctoring**:
  - Live webcam feed calibration on the setup screen to verify candidate face alignment and lighting.
  - Continuous real-time frame monitoring during live interviews.
  - Automatic detection of **Multiple People in Frame** (unauthorized assistance).
  - Automatic detection of **Absent Candidate / No Face in Frame**.
  - Real-time prohibited device/object detection (e.g. mobile phones, auxiliary books) via TensorFlow.js COCO-SSD and server-side OpenCV.
- **Tab Switching Guard & Mark Reduction**:
  - Monitors window blur and browser tab switching using HTML5 Visibility API.
  - Triggers audible warning alarms and on-screen violation modals.
  - **Algorithmic Score Penalty**: Automatically deducts **5% from the candidate's final score** per tab switch occurrence.
  - Maintains a real-time integrity rating (0-100%) and event audit trail.
- **Multi-Discipline Support**:
  - **Technical**: Python, Java, SQL, DBMS, OOP, Data Structures, Machine Learning, Artificial Intelligence, Web Development.
  - **HR & Behavioral**: Situational scenarios, conflict resolution, STAR framework responses.
  - **Aptitude**: Quantitative reasoning, logical deductions, math problem solving.
- **Dual Voice & Text Input**:
  - Browser **Web Speech API** for real-time speech-to-text voice input.
  - Visual animated microphone waveform and pulse indicator.
  - Editable transcription (candidates can edit or supplement speech text).
  - Browser **SpeechSynthesis** to read interview questions aloud to the candidate.
- **AI & Rule-Based Dual Engine**:
  - Real integration with **Google Gemini API** (`gemini-1.5-flash`) and **OpenAI API** (`gpt-4o-mini`).
  - Clearly labeled **Offline Rule-Based Evaluator (Demo Mode)** that executes context-aware NLP evaluation when API keys are not supplied.
  - **Honest System Transparency**: Never misrepresents mock/offline evaluations as genuine AI.
- **Performance Analytics**:
  - Dynamic **Chart.js** performance trend line graphs over time.
  - Multi-dimensional competency radar charts displaying scores across the 4 rubric dimensions.
  - Question-by-question score progression bar charts.
- **Downloadable PDF Assessment Reports**:
  - Generated using **ReportLab** with candidate details, rubric benchmarks, question-wise scores, AI feedback, model answers, and action plans.
- **Candidate Dashboard & History**:
  - Real-time KPIs (Total interviews, Average score, Latest score, Completion status).
  - Historical interview repository with filterable records and PDF downloads.
- **Comprehensive Admin Panel**:
  - Platform-wide statistics, active interview monitor, and category distribution donut charts.
  - Question bank CRUD (Add, Edit, Delete questions with reference answers and keywords).
  - Candidate management (Search, inspect individual candidate interview profiles).

---

## 3. Technology Stack

- **Frontend**:
  - HTML5, CSS3, JavaScript (ES6+)
  - Bootstrap 5.3 & Bootstrap Icons
  - Chart.js 4.4 (Trend charts, Radar charts, Progression bars)
  - Browser Web Speech API (`SpeechRecognition` & `SpeechSynthesis`)
- **Backend**:
  - Python 3.11+
  - Flask 3.1
  - Flask-SQLAlchemy 3.1 & SQLAlchemy 2.1 ORM
  - Flask-Login 0.6 (Session-based secure authentication)
  - Werkzeug (PBKDF2/SHA-256 password hashing)
- **Database**:
  - SQLite (Local development) & SQLAlchemy ORM (MySQL/PostgreSQL production-ready)
- **AI & NLP**:
  - Google Gemini API (`google-generativeai`)
  - OpenAI API (`openai`)
  - Rule-Based Contextual NLP Evaluator (Keyword & semantic matching fallback)
- **Reporting & Testing**:
  - ReportLab 4.5 (Vector PDF report generation)
  - Pytest 8.4 (Automated testing suite)

---

## 4. Project Directory Structure

```
AI_Interview_System/
│
├── app.py                      # Application entry point & factory
├── config.py                   # Configuration & environment loader
├── init_db.py                  # Database initialization & seeding script
├── seed_questions.py           # 50+ Seed interview questions & accounts
├── requirements.txt            # Python dependencies
├── .env.example                # Template for environment variables
├── .env                        # Local environment variables
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete system documentation
│
├── models/                     # SQLAlchemy Database Models
│   ├── __init__.py             # DB instance & model exports
│   ├── user.py                 # User model (Candidates & Admins)
│   ├── question.py             # Question bank repository model
│   ├── interview.py            # Interview session & Response models
│   └── result.py               # Aggregated interview result model
│
├── routes/                     # Application Blueprints
│   ├── __init__.py             # Route blueprint exports
│   ├── auth.py                 # Candidate/Admin login, register, logout
│   ├── candidate.py            # Candidate dashboard, history, profile
│   ├── interview.py            # Interview setup, live engine, submit, report, PDF
│   └── admin.py                # Admin dashboard, questions CRUD, candidate logs
│
├── services/                   # Business Logic & External Services
│   ├── __init__.py             # Service exports
│   ├── ai_service.py           # Gemini & OpenAI API clients
│   ├── evaluation_service.py   # Rubric dispatcher & rule-based evaluator
│   └── report_service.py       # ReportLab PDF report generator
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Base layout with navbar, footer, and theme toggle
│   ├── index.html              # Marketing & feature showcase landing page
│   ├── login.html              # Secure login form with demo credentials
│   ├── register.html           # Candidate registration form
│   ├── dashboard.html          # Candidate KPI dashboard & Chart.js analytics
│   ├── interview_setup.html    # Configuration screen (Topic, count, mode)
│   ├── interview.html          # Live interview engine (Timer, voice, AI submit)
│   ├── results.html            # Scorecard, rubric radar, feedback, and answers
│   ├── history.html            # Filterable interview history table
│   ├── profile.html            # Profile management & password updates
│   └── admin/                  # Administrative Panel Templates
│       ├── dashboard.html      # Platform overview & system KPIs
│       ├── questions.html      # Question management with modals (CRUD)
│       ├── candidates.html     # Registered candidates search & table
│       ├── candidate_detail.html # Individual candidate interview history
│       ├── interviews.html     # Platform-wide interview logs
│       └── interview_detail.html # Detailed interview inspection
│
├── static/                     # Static Assets
│   ├── css/
│   │   └── style.css           # Custom SaaS stylesheet (indigo/purple/blue)
│   ├── js/
│   │   ├── main.js             # Theme toggle, alert dismiss, tooltips
│   │   ├── voice.js            # Web Speech STT & SpeechSynthesis TTS
│   │   └── interview.js        # Live timer, word count, AJAX submit & loader
│   └── images/
│       └── logo.svg            # System brand SVG vector logo
│
├── tests/                      # Automated Pytest Suite
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures, test client & memory DB
│   ├── test_auth.py            # Authentication, validation, and hash tests
│   ├── test_interview.py       # Interview creation, submission, and auth tests
│   ├── test_evaluation.py      # Rubric weights (40/25/20/15) & NLP tests
│   ├── test_reports.py         # PDF generation and download route tests
│   └── test_admin.py           # Role-based access and question CRUD tests
│
└── instance/                   # SQLite database storage
    └── interview_system.db     # SQLite relational database
```

---

## 5. Installation & Execution Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12 installed on your machine.
- Git (optional, for cloning).

### Step 1: Clone or Navigate to the Workspace
```powershell
cd "C:\Users\Hp\.gemini\antigravity\scratch\AI_Interview_System"
```

### Step 2: Create and Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell:
.\venv\Scripts\Activate.ps1

# (Or on Windows Command Prompt:)
# .\venv\Scripts\activate.bat
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Open `.env` in any editor to customize your settings:
```ini
SECRET_KEY=ai-interview-system-dev-secret-key-99210
DATABASE_URL=sqlite:///instance/interview_system.db

# Choose 'gemini' or 'openai'
AI_PROVIDER=gemini

# Paste your Gemini API key from https://aistudio.google.com/
GEMINI_API_KEY=

# Or your OpenAI API key from https://platform.openai.com/api-keys
OPENAI_API_KEY=

# 'auto' uses AI API if key is present; otherwise falls back to labeled rule-based evaluator
EVALUATION_MODE=auto
```

*(Note: If you do not have an API key right now, keep `GEMINI_API_KEY=` blank. The system runs seamlessly in **Rule-Based Offline Evaluator (Demo Mode)**, which evaluates answers using keyword and semantic metrics).*

### Step 5: Initialize and Seed the Database
Run the database seeder to create tables and populate 50+ interview questions and default accounts:
```powershell
python init_db.py
```

### Step 6: Start the Application
```powershell
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 6. Pre-Configured Test Accounts

| Role | Email | Password | Access Privileges |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@aiinterview.com` | `Admin@123` | Question bank CRUD, all candidate logs, system KPIs |
| **Candidate** | `candidate@aiinterview.com` | `Candidate@123` | Take interviews, view dashboard, download PDF reports |

*(New candidates can also register directly on the `/register` page).*

---

## 7. Running the Automated Test Suite

The project includes 23 automated tests covering authentication, question retrieval, rubric scoring math, evaluation fallback, PDF generation, and admin authorization.

Run pytest:
```powershell
pytest -v
```

Expected output:
```
tests/test_admin.py::test_candidate_forbidden_from_admin_dashboard PASSED
tests/test_admin.py::test_admin_access_dashboard PASSED
tests/test_admin.py::test_admin_add_question PASSED
tests/test_admin.py::test_admin_edit_question PASSED
tests/test_admin.py::test_admin_delete_question PASSED
tests/test_admin.py::test_admin_candidate_list PASSED
tests/test_auth.py::test_candidate_registration PASSED
tests/test_auth.py::test_duplicate_registration_prevention PASSED
tests/test_auth.py::test_password_mismatch_registration PASSED
tests/test_auth.py::test_candidate_login_success PASSED
tests/test_auth.py::test_admin_login_success PASSED
tests/test_auth.py::test_invalid_credentials PASSED
tests/test_auth.py::test_logout PASSED
tests/test_evaluation.py::test_rubric_weights_calculation PASSED
tests/test_evaluation.py::test_rubric_clamping_bounds PASSED
tests/test_evaluation.py::test_rule_based_evaluator_keywords PASSED
tests/test_evaluation.py::test_empty_answer_handling PASSED
tests/test_interview.py::test_interview_setup_and_creation PASSED
tests/test_interview.py::test_answer_submission_and_evaluation PASSED
tests/test_interview.py::test_prevent_duplicate_submission PASSED
tests/test_interview.py::test_unauthorized_interview_access PASSED
tests/test_reports.py::test_pdf_report_generation PASSED
tests/test_reports.py::test_pdf_download_route PASSED

======================= 23 passed in 7.97s =======================
```

---

## 8. Scoring Rubric Specifications

The scoring algorithm calculates performance using a weighted average of four criteria scored from 0.0 to 10.0, followed by proctoring penalty adjustments:

$$\text{Raw AI Score} = (0.40 \times \text{Correctness}) + (0.25 \times \text{Relevance}) + (0.20 \times \text{Completeness}) + (0.15 \times \text{Clarity})$$

$$\text{Tab Switch Penalty} = \text{tab\_switch\_count} \times 0.5 \text{ pts } (5\% \text{ per occurrence})$$

$$\text{Frame / Object Violation Penalty} = \text{violations\_count} \times 0.5 \text{ pts } (5\% \text{ per occurrence})$$

$$\text{Net Final Score} = \max(0.0, \text{Raw AI Score} - \text{Tab Switch Penalty} - \text{Violation Penalty})$$

$$\text{Final Percentage} = \text{Net Final Score} \times 10\%$$

$$\text{Integrity Rating} = \max(0\%, 100\% - (\text{tab\_switch\_count} \times 5\%) - (\text{violations\_count} \times 5\%))$$

Each response receives:
1. **Numeric Scores**: Correctness, Relevance, Completeness, Clarity, and Overall Score.
2. **Specific Strengths**: Identified accurate concepts and terminology.
3. **Specific Weaknesses**: Missed definitions, edge cases, or trade-offs.
4. **Constructive Feedback**: Direct guidance tailored to the response.
5. **Model Answer**: Standard high-scoring reference answer.
6. **Improvement Tips**: Practical actionable advice for subsequent rounds.

---

## 9. Troubleshooting & FAQ

- **Microphone not working**:
  Ensure you are using Google Chrome, Microsoft Edge, or Apple Safari (browsers with native Web Speech API support). Also make sure you have granted microphone permissions in browser settings. If not supported, simply type in the answer editor.
- **SQLite "unable to open database file"**:
  Run `python init_db.py` directly from the project directory. The application resolves absolute database paths automatically.
- **Port 5000 is already in use**:
  Run `python app.py` and modify the port in `app.run(port=5050)` if needed.

---

## 10. Academic Project Declaration

This project was engineered to satisfy all requirements for a **B.Tech Computer Science and Engineering Minor Project**, demonstrating expertise in full-stack architecture, relational database design, natural language processing, audio APIs, automated evaluation rubrics, and automated testing.
