from datetime import datetime, timezone
from fastapi import Depends, FastAPI, status, HTTPException
from pydantic import BaseModel, Field, computed_field
from typing import List, Optional
from enum import Enum
import sqlite3

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Task(BaseModel):
    id: int
    entry: str
    priority: Priority = Field(default="medium")
    due: datetime
    completed: bool = False
    completed_at: datetime | None = Field(examples=[None])

    @computed_field
    def is_overdue(self) -> bool:
        return self.due < datetime.now(timezone.utc) and self.completed_at is None

class TaskUpdate(BaseModel):
    entry: Optional[str]
    priority: Optional[Priority]
    due: Optional[datetime]
    completed: Optional[bool] = Field(default=None)
    completed_at: Optional[datetime] = Field(examples=[None])

class PaginatedResponse(BaseModel):
    data: List[Task]
    pagination: dict

app = FastAPI(title="TaskFlow API", description="TaskFlow")

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

init_db()

def row_to_task(row: tuple) -> Task:
    return Task(
        id=row[0],
        entry=row[1],
        priority=Priority(row[2]),
        due=datetime.fromisoformat(row[3]),
        completed=bool(row[4]),
        completed_at=datetime.fromisoformat(row[5]) if row[5] else None
    )

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

@app.get("/tasks", status_code=status.HTTP_200_OK ,response_model=PaginatedResponse)
def read_entries(skip: int = 0,
                 limit: int = 100,
                 order: str = "asc",
                 priority: Priority | None = None,
                 due_before: datetime | None = None,
                 due_after: datetime | None = None,
                 sort: str = "id",
                 db: sqlite3.Connection = Depends(load_db)
                ):
    end = skip + limit
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    tasks = [row_to_task(row) for row in rows]
    reverse = order == "desc"
    if priority is not None:
        tasks = [t for t in tasks if t.priority.value.lower() == priority.lower()]
    if due_before is not None:
        tasks = [t for t in tasks if t.due <= due_before]
    if due_after is not None:
        tasks = [t for t in tasks if t.due >= due_after]
    match sort:
        case "priority": key = lambda t: t.priority.value
        case "entry": key = lambda t: t.entry.lower()
        case _: key = lambda t: t.id
    tasks = sorted(tasks, key=key, reverse=reverse)
    return {
        "data": tasks[skip:end],
        "pagination": {
            "total": len(tasks),
            "skip": skip,
            "limit": limit,
            "has_more": skip + limit < len(tasks)
        }
    }

@app.get("/tasks/{task_id}", status_code=status.HTTP_200_OK, response_model=Task)
def read_entry(task_id: int, db: sqlite3.Connection = Depends(load_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return row_to_task(row)

@app.patch("/tasks/{task_id}")
def update_entry(task_id: int, update_data: TaskUpdate, db: sqlite3.Connection = Depends(load_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    set_parts = []
    params = []
    if update_data.entry is not None:
        set_parts.append("entry = ?")
        params.append(update_data.entry)
    if update_data.priority is not None:
        set_parts.append("priority = ?")
        params.append(update_data.priority.value)
    if update_data.due is not None:
        set_parts.append("due = ?")
        params.append(update_data.due.isoformat())
    if update_data.completed is not None:
        set_parts.append("completed = ?")
        params.append(int(update_data.completed))
        completed_at = datetime.now(timezone.utc).isoformat() if update_data.completed else None
        set_parts.append("completed_at = ?")
        params.append(completed_at)
    if update_data.completed_at is not None:
        set_parts.append("completed_at = ?")
        params.append(update_data.completed_at.isoformat() if update_data.completed_at else None)
    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")
    params.append(task_id)
    update = f"UPDATE tasks SET {', '.join(set_parts)} WHERE id = ?"
    cursor.execute(update, params)
    db.commit()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return row_to_task(cursor.fetchone())

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry(task_id: int, db: sqlite3.Connection = Depends(load_db)):
    cursor = db.cursor()
    delete = "DELETE FROM tasks WHERE id = ?"
    cursor.execute(delete, (task_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return None

@app.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=Task)
def create_entry(task: Task, db: sqlite3.Connection = Depends(load_db)):
    cursor = db.cursor() 
    insert = '''
        INSERT INTO tasks(entry, priority, due, completed, completed_at)
        VALUES(?, ?, ?, ?, ?)
    '''
    values = (
        task.entry,
        task.priority.value,
        task.due.isoformat(),
        int(task.completed),
        task.completed_at.isoformat() if task.completed_at else None
    )
    cursor.execute(insert, values)
    db.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
    return row_to_task(cursor.fetchone())

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