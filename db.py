from datetime import datetime
from models import Task, Priority
import sqlite3

DB_PATH = "tasks.db"

db_table = '''
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY,
        entry TEXT NOT NULL,
        priority TEXT NOT NULL,
        due DATETIME,
        completed BOOLEAN,
        completed_at DATETIME
    )
'''

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(db_table)
        conn.commit()

def load_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def row_to_task(row: tuple) -> Task:
    return Task(
        id=row[0],
        entry=row[1],
        priority=Priority(row[2]),
        due=datetime.fromisoformat(row[3]),
        completed=bool(row[4]),
        completed_at=datetime.fromisoformat(row[5]) if row[5] else None
    )