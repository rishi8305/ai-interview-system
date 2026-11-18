"""
Migration script from SQLite to MongoDB for AI Interview System.
Transfers all tables and data from instance/interview_system.db into MongoDB (ai_interview_db).
"""

import os
import sqlite3
import json
from datetime import datetime
from pymongo import MongoClient

SQLITE_PATH = r"C:\Users\Hp\.gemini\antigravity\scratch\AI_Interview_System\instance\interview_system.db"
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/ai_interview_db")
DB_NAME = "ai_interview_db"


def parse_dt(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except Exception:
            pass
    return None


def run_migration():
    if not os.path.exists(SQLITE_PATH):
        print(f"[-] SQLite database not found at {SQLITE_PATH}")
        return

    print(f"[*] Connecting to SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    print(f"[*] Connecting to MongoDB: {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Clean existing test data from collections
    for coll in ["users", "questions", "interviews", "responses", "results", "proctoring_logs"]:
        db[coll].drop()

    counters = {}

    # 1. USERS
    cur.execute("SELECT * FROM users")
    users = [dict(r) for r in cur.fetchall()]
    max_user_id = 0
    for u in users:
        u_id = int(u["id"])
        max_user_id = max(max_user_id, u_id)
        doc = {
            "_id": u_id,
            "name": u["name"],
            "email": u["email"].lower().strip(),
            "password_hash": u["password_hash"],
            "role": u.get("role", "candidate"),
            "created_at": parse_dt(u.get("created_at")),
        }
        db.users.replace_one({"_id": u_id}, doc, upsert=True)
    db.users.create_index("email", unique=True)
    counters["users.id"] = max_user_id
    print(f"[+] Migrated {len(users)} users to MongoDB.")

    # 2. QUESTIONS
    cur.execute("SELECT * FROM questions")
    questions = [dict(r) for r in cur.fetchall()]
    max_q_id = 0
    for q in questions:
        q_id = int(q["id"])
        max_q_id = max(max_q_id, q_id)
        doc = {
            "_id": q_id,
            "category": q["category"],
            "topic": q.get("topic"),
            "difficulty": q.get("difficulty", "Medium"),
            "question_text": q["question_text"],
            "reference_answer": q.get("reference_answer"),
            "keywords": q.get("keywords"),
            "is_generated": bool(q.get("is_generated", 0)),
            "created_at": parse_dt(q.get("created_at")),
        }
        db.questions.replace_one({"_id": q_id}, doc, upsert=True)
    counters["questions.id"] = max_q_id
    print(f"[+] Migrated {len(questions)} questions to MongoDB.")

    # 3. INTERVIEWS
    cur.execute("SELECT * FROM interviews")
    interviews = [dict(r) for r in cur.fetchall()]
    max_int_id = 0
    for it in interviews:
        int_id = int(it["id"])
        max_int_id = max(max_int_id, int_id)
        # Parse question IDs JSON
        q_ids = []
        if it.get("question_ids_json"):
            try:
                q_ids = json.loads(it["question_ids_json"])
            except Exception:
                pass

        doc = {
            "_id": int_id,
            "user_id": int(it["user_id"]),
            "category": it["category"],
            "topic": it.get("topic"),
            "difficulty": it.get("difficulty", "Medium"),
            "question_count": int(it.get("question_count", 5)),
            "input_mode": it.get("input_mode", "text"),
            "status": it.get("status", "in_progress"),
            "evaluation_mode": it.get("evaluation_mode", "Rule-Based (Offline Demo)"),
            "total_score": float(it.get("total_score") or 0.0),
            "raw_score": float(it.get("raw_score") or 0.0),
            "tab_switch_count": int(it.get("tab_switch_count") or 0),
            "violations_count": int(it.get("violations_count") or 0),
            "proctoring_penalty": float(it.get("proctoring_penalty") or 0.0),
            "integrity_score": float(it.get("integrity_score") or 100.0),
            "resume_text": it.get("resume_text"),
            "resume_filename": it.get("resume_filename"),
            "question_ids_json": it.get("question_ids_json") or json.dumps(q_ids),
            "started_at": parse_dt(it.get("started_at")),
            "completed_at": parse_dt(it.get("completed_at")),
        }
        db.interviews.replace_one({"_id": int_id}, doc, upsert=True)
    counters["interviews.id"] = max_int_id
    print(f"[+] Migrated {len(interviews)} interviews to MongoDB.")

    # 4. RESPONSES
    cur.execute("SELECT * FROM responses")
    responses = [dict(r) for r in cur.fetchall()]
    max_resp_id = 0
    for resp in responses:
        r_id = int(resp["id"])
        max_resp_id = max(max_resp_id, r_id)
        doc = {
            "_id": r_id,
            "interview_id": int(resp["interview_id"]),
            "question_id": int(resp["question_id"]),
            "answer_text": resp["answer_text"],
            "correctness_score": float(resp.get("correctness_score") or 0.0),
            "relevance_score": float(resp.get("relevance_score") or 0.0),
            "completeness_score": float(resp.get("completeness_score") or 0.0),
            "clarity_score": float(resp.get("clarity_score") or 0.0),
            "overall_score": float(resp.get("overall_score") or 0.0),
            "feedback": resp.get("feedback"),
            "strengths_json": resp.get("strengths_json"),
            "weaknesses_json": resp.get("weaknesses_json"),
            "suggested_answer": resp.get("suggested_answer"),
            "improvement_tips_json": resp.get("improvement_tips_json"),
            "created_at": parse_dt(resp.get("created_at")),
        }
        db.responses.replace_one({"_id": r_id}, doc, upsert=True)
    counters["responses.id"] = max_resp_id
    print(f"[+] Migrated {len(responses)} responses to MongoDB.")

    # 5. RESULTS
    cur.execute("SELECT * FROM results")
    results = [dict(r) for r in cur.fetchall()]
    max_res_id = 0
    for res in results:
        res_id = int(res["id"])
        max_res_id = max(max_res_id, res_id)
        doc = {
            "_id": res_id,
            "interview_id": int(res["interview_id"]),
            "user_id": int(res["user_id"]),
            "total_score": float(res.get("total_score") or 0.0),
            "percentage": float(res.get("percentage") or 0.0),
            "raw_score": float(res.get("raw_score") or 0.0),
            "proctoring_penalty": float(res.get("proctoring_penalty") or 0.0),
            "tab_switch_count": int(res.get("tab_switch_count") or 0),
            "violations_count": int(res.get("violations_count") or 0),
            "integrity_score": float(res.get("integrity_score") or 100.0),
            "correctness_avg": float(res.get("correctness_avg") or 0.0),
            "relevance_avg": float(res.get("relevance_avg") or 0.0),
            "completeness_avg": float(res.get("completeness_avg") or 0.0),
            "clarity_avg": float(res.get("clarity_avg") or 0.0),
            "strengths_json": res.get("strengths_json"),
            "weaknesses_json": res.get("weaknesses_json"),
            "recommendations_json": res.get("recommendations_json"),
            "proctoring_summary_json": res.get("proctoring_summary_json"),
            "created_at": parse_dt(res.get("created_at")),
        }
        db.results.replace_one({"_id": res_id}, doc, upsert=True)
    counters["results.id"] = max_res_id
    print(f"[+] Migrated {len(results)} results to MongoDB.")

    # 6. PROCTORING LOGS
    cur.execute("SELECT * FROM proctoring_logs")
    logs = [dict(r) for r in cur.fetchall()]
    max_log_id = 0
    for l in logs:
        l_id = int(l["id"])
        max_log_id = max(max_log_id, l_id)
        doc = {
            "_id": l_id,
            "interview_id": int(l["interview_id"]),
            "event_type": l["event_type"],
            "severity": l.get("severity", "medium"),
            "description": l["description"],
            "penalty_applied": float(l.get("penalty_applied") or 0.0),
            "timestamp": parse_dt(l.get("timestamp")),
        }
        db.proctoring_logs.replace_one({"_id": l_id}, doc, upsert=True)
    counters["proctoring_logs.id"] = max_log_id
    print(f"[+] Migrated {len(logs)} proctoring logs to MongoDB.")

    # Update sequence counters for mongoengine
    for counter_name, next_val in counters.items():
        db["mongoengine.counters"].replace_one(
            {"_id": counter_name},
            {"_id": counter_name, "next": next_val + 1},
            upsert=True
        )

    sqlite_conn.close()
    print("[SUCCESS] All SQLite data migrated successfully to MongoDB!")


if __name__ == "__main__":
    run_migration()
