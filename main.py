from datetime import date
from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from typing import List
from enum import Enum
import json
import os

class Priority(str, Enum):
    High = "High"
    Medium = "Medium"
    Low = "Low"

class Task(BaseModel):
    id: int
    entry: str
    priority: Priority
    due: date

app = FastAPI(title="TaskFlow API", description="TaskFlow")

DB_PATH = "tasks.json"
cached_db: List[Task] = []

def save_db():
    with open(DB_PATH, "w") as file:
        json.dump([task.dict() for task in cached_db], file, indent=2, default=str)

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
    return {"message": "Welcome to the TaskFlow API"}

@app.get("/tasks", response_model=List[Task])
def read_entries(skip: int = 0, limit: int = 100, order: str = "asc"):
    if order == "desc":
        reverse = True
    else:
        reverse = False
    end = skip + limit
    return sorted(cached_db[skip:end], key=lambda t: t.id, reverse=reverse)

@app.get("/tasks/{task_id}")
def read_entry(task_id: int):
    for task in cached_db:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@app.put("/tasks/{task_id}")
def update_entry(task_id: int, updated_task: Task):
    for i, task in enumerate(cached_db):
        if task.id == task_id:
            updated = task.model_copy(update=updated_task.model_dump(exclude_unset=True))
            cached_db[i] = updated
            save_db()
            return updated
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@app.delete("/tasks/{task_id}")
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