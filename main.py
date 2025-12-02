from datetime import datetime, timezone
from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel, Field, computed_field
from typing import List, Optional
from enum import Enum
import json
import os

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
    id: Optional[int]
    entry: Optional[str]
    priority: Optional[Priority]
    due: Optional[datetime]
    completed: Optional[bool] = Field(default=None)
    completed_at: Optional[datetime] = Field(examples=[None])

class PaginatedResponse(BaseModel):
    data: List[Task]
    pagination: dict

app = FastAPI(title="TaskFlow API", description="TaskFlow")

DB_PATH = "tasks.json"
cached_db: List[Task] = []

def save_db():
    with open(DB_PATH, "w") as file:
        json.dump([task.model_dump() for task in cached_db], file, indent=2, default=str)

def load_db():
    global cached_db
    if not os.path.exists(DB_PATH):
        cached_db = []
        save_db()
    else:
        with open(DB_PATH, "r") as file:
            content = file.read().strip()
            if not content:
                cached_db = []
            else:
                try:
                    raw = json.loads(content)
                    cached_db = [Task(**item) for item in raw]
                except json.JSONDecodeError:
                    cached_db = []
                    save_db()
load_db()

@app.get("/")
def home():
    return {
        "message": "TaskFlow API",
        "version": "1.0",
        "tasks_count": len(cached_db),
        "current_date": str(datetime.today()),
    }

@app.get("/tasks", status_code=status.HTTP_200_OK ,response_model=PaginatedResponse)
def read_entries(skip: int = 0,
                 limit: int = 100,
                 order: str = "asc",
                 priority: Priority | None = None,
                 due_before: datetime | None = None,
                 due_after: datetime | None = None,
                 sort: str = "id"):
    tasks = cached_db.copy()
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
    end = skip + limit
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
def read_entry(task_id: int):
    for task in cached_db:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@app.patch("/tasks/{task_id}")
def update_entry(task_id: int, update: TaskUpdate):
    for i, task in enumerate(cached_db):
        if task.id == task_id:
            updated = task.model_copy(update=update.model_dump(exclude_unset=True))
            updated.completed_at = datetime.now(timezone.utc) if updated.completed else None
            cached_db[i] = updated
            save_db()
            return updated
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry(task_id: int):
    for i, task in enumerate(cached_db):
        if task.id == task_id:
            cached_db.pop(i)
            save_db()
            return
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@app.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=Task)
def create_entry(task: Task):
    new_id = max([t.id for t in cached_db], default=0) + 1
    new_task = task.model_copy(update={"id": new_id})
    cached_db.append(new_task)
    save_db()
    return new_task

@app.get("/search")
def search(q: str):
    search_results = []
    split_query = q.lower().split()
    for task in cached_db:
        if any(term in task.entry.lower() for term in split_query):
            result = task.model_copy()
            search_results.append(result)
    return search_results