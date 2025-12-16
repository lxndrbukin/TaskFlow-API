from datetime import datetime
from models import Task, Priority
import sqlite3

DB_PATH = "taskflow.db"

tasks_db_table = '''
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY,
        entry TEXT NOT NULL,
        priority TEXT NOT NULL,
        due DATETIME,
        completed BOOLEAN,
        completed_at DATETIME
    )
'''

users_db_table = '''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        signup_date DATETIME DEFAULT CURRENT_TIMESTAMP
    )
'''

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(tasks_db_table)
        conn.execute(users_db_table)
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