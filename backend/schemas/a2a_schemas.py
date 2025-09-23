from __future__ import annotations

from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    id: str
    agent: str
    input: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    on_error: Literal["stop", "continue"] = "stop"


class WorkflowRequest(BaseModel):
    run_id: str
    tasks: List[TaskSpec]


class TaskEvent(BaseModel):
    task_id: str
    type: Literal["TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED"]
    message: str = ""


class WorkflowResult(BaseModel):
    run_id: str
    status: Literal["completed", "failed", "paused"]
    context: Dict[str, Any] = Field(default_factory=dict)
    events: List[TaskEvent] = Field(default_factory=list)
    error: Optional[str] = None

