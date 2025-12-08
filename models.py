from datetime import datetime, timezone
from pydantic import BaseModel, Field, computed_field
from typing import List, Optional
from enum import Enum

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