from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException
import sqlite3
from db import init_db, load_db, row_to_task
from routers.tasks import tasks_router
from routers.auth import auth_router

app = FastAPI(title="TaskFlow API", description="TaskFlow")
app.include_router(tasks_router)
app.include_router(auth_router)

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
def search(q: str, limit: int = 20, db: sqlite3.Connection = Depends(load_db)):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query can't be empty")
    stop_words = set(["and", "but", "the", "a", "an", "or", "in", "on"])
    cursor = db.cursor()
    split_search_query = [term for term in q.lower().split() if term not in stop_words]
    if not split_search_query:
        return []
    where_clauses = []
    for term in split_search_query:
        where_clauses.append(f"LOWER(entry) LIKE ?")
    params = [f"%{term}%" for term in split_search_query]
    base_query = "SELECT * FROM tasks"
    if where_clauses:
        base_query += f" WHERE {' OR '.join(where_clauses)}"
    base_query += f" LIMIT ?"
    params.append(limit)
    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    results = [row_to_task(row) for row in rows]
    return results