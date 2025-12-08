from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException
import sqlite3
from db import init_db, load_db, row_to_task
from routers.tasks import tasks_router

app = FastAPI(title="TaskFlow API", description="TaskFlow")
app.include_router(tasks_router)

init_db()

@app.get("/")
def home(db: sqlite3.Connection = Depends(load_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    return {
        "message": "TaskFlow API",
        "version": "1.0",
        "tasks_count": count,
        "current_date": str(datetime.today()),
    }

@app.get("/search")
def search(q: str, db: sqlite3.Connection = Depends(load_db)):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query can't be empty")
    cursor = db.cursor()
    split_query = q.lower().split()
    where_clauses = []
    for term in split_query:
        where_clauses.append(f"LOWER(entry) LIKE ?")
    params = [f"%{term}%" for term in split_query]
    search_tasks = f"""
        SELECT * FROM tasks 
        WHERE {' OR '.join(where_clauses)} 
    """
    cursor.execute(search_tasks, params)
    rows = cursor.fetchall()
    results = [row_to_task(row) for row in rows]
    return results