from datetime import date
from fastapi import FastAPI, status
from pydantic import BaseModel
from typing import List
import json
import os

class Task(BaseModel):
    id: int
    entry: str
    priority: str
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
def read_entries():
    return cached_db

@app.get("/tasks/{task_id}")
def read_entry(task_id: int):
    for task in cached_db:
        if task.id == task_id:
            return task
    return {"error": f"Task with ID {task_id} not found"}

@app.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=Task)
def create_entry(task: Task):
    new_id = max([t.id for t in cached_db], default=0) + 1
    new_task = task.model_copy(update={"id": new_id})
    cached_db.append(new_task)
    save_db()
    return new_task