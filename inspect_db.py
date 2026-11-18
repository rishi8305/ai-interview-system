import sqlite3

conn = sqlite3.connect(r'C:\Users\Hp\.gemini\antigravity\scratch\AI_Interview_System\instance\interview_system.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in c.fetchall()]
print('SQLite tables:', tables)
for t in tables:
    if t != 'sqlite_sequence':
        c.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {c.fetchone()[0]} rows")
