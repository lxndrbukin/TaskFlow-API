from datetime import datetime, timezone
import sqlite3
from fastapi import APIRouter
from fastapi import Depends, status, HTTPException
from models import Task, TaskUpdate, Priority, PaginatedResponse
from db import load_db, row_to_task

tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])

@tasks_router.get("/", status_code=status.HTTP_200_OK ,response_model=PaginatedResponse)
def read_entries(skip: int = 0,
                 limit: int = 100,
                 order: str = "asc",
                 priority: Priority | None = None,
                 due_before: datetime | None = None,
                 due_after: datetime | None = None,
                 sort: str = "id",
                 db: sqlite3.Connection = Depends(load_db)
                ):
    cursor = db.cursor()
    where_clauses = []
    params = []
    reverse = order == "desc"
    if priority is not None:
        where_clauses.append("priority = ?")
        params.append(priority.value)
    if due_before is not None:
        where_clauses.append("due <= ?")
        params.append(due_before.isoformat())
    if due_after is not None:
        where_clauses.append("due >= ?")
        params.append(due_after.isoformat())
    params += [limit, skip]
    sort_map = {"id": "id", "priority": "priority", "entry": "LOWER(entry)"}.get(sort, "id")
    base_query = "SELECT * FROM tasks"
    if where_clauses:
        base_query += f" WHERE {' AND '.join(where_clauses)}"
    base_query += f" ORDER BY {sort_map} {'DESC' if reverse else 'ASC'} LIMIT ? OFFSET ?"
    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    tasks = [row_to_task(row) for row in rows]
    return {
        "data": tasks,
        "pagination": {
            "total": len(tasks),
            "skip": skip,
            "limit": limit
        }
    }

@tasks_router.get("/{task_id}", status_code=status.HTTP_200_OK, response_model=Task)
def read_entry(task_id: int, db: sqlite3.Connection = Depends(load_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return row_to_task(row)

@tasks_router.post("/", status_code=status.HTTP_201_CREATED, response_model=Task)
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

@tasks_router.patch("/{task_id}")
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

@tasks_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry(task_id: int, db: sqlite3.Connection = Depends(load_db)):
    cursor = db.cursor()
    delete = "DELETE FROM tasks WHERE id = ?"
    cursor.execute(delete, (task_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return None