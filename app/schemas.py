from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

TaskType = Literal["send_email", "generate_report", "demo_fail"]

class JobCreate(BaseModel):
    task_type: TaskType
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    max_attempts: int = Field(default=3, ge=1, le=10)
    scheduled_for: datetime | None = None

class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_type: str
    payload: dict
    status: str
    priority: int
    attempts: int
    max_attempts: int
    result: dict | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

class MetricsOut(BaseModel):
    total: int
    queued: int
    running: int
    succeeded: int
    retrying: int
    dead_letter: int
