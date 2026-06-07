from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


TaskStatus = Literal["received", "fetching_context", "analyzing", "completed", "failed"]
SourceKind = Literal["issue", "pull_request", "webhook_simulation"]


class AnalyzeRequest(BaseModel):
    source_url: HttpUrl
    auto_comment: bool = False
    apply_labels: bool = False


class WebhookSimulationRequest(BaseModel):
    event_type: str = Field(default="issues", examples=["issues", "pull_request"])
    payload: Dict[str, Any]


class AnalysisResult(BaseModel):
    category: str
    priority: str
    confidence_score: int = Field(ge=0, le=100)
    summary: str
    suggested_labels: List[str]
    impact_modules: List[str]
    probable_causes: List[str]
    action_plan: List[str]
    test_plan: List[str]
    acceptance_criteria: List[str]
    review_checklist: List[str]
    maintainer_comment: str
    risks: List[str]


class TaskOut(BaseModel):
    id: str
    kind: SourceKind
    status: TaskStatus
    source_url: Optional[str] = None
    repo_full_name: Optional[str] = None
    number: Optional[int] = None
    title: Optional[str] = None
    analysis: Optional[AnalysisResult] = None
    automation_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaskCreated(BaseModel):
    task_id: str
    status: TaskStatus


class HealthOut(BaseModel):
    status: str
    service: str
    version: str
    llm_configured: bool
    github_configured: bool
    webhook_secret_configured: bool

