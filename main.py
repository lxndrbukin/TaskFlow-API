from datetime import date
from fastapi import FastAPI, status
from pydantic import BaseModel
from typing import List

class Task(BaseModel):
	id: int
	entry: str
	priority: str
	due: date

fake_db = []

app = FastAPI(title="TaskFlow API", description="TaskFlow")

@app.get("/")
def home():
	return {"message": "Welcome to the TaskFlow API"}

@app.get("/tasks", response_model=List[Task])
def read_tasks():
	return fake_db

@app.get("/tasks/{task_id}")
def read_task(task_id: int):
	for task in fake_db:
		if task.id == task_id:
			return task
	return {"error": f"Task with ID {task_id} not found"}

@app.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=Task)
def create_entry(task: Task):
	fake_db.append(task)
	return task