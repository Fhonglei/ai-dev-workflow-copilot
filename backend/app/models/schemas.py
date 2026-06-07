from datetime import datetime
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


TaskStatus = Literal["received", "fetching_context", "analyzing", "completed", "failed"]
SourceKind = Literal["issue", "pull_request", "webhook_simulation", "ci_failure"]


class AnalyzeRequest(BaseModel):
    source_url: HttpUrl
    auto_comment: bool = False
    apply_labels: bool = False

    @field_validator("source_url")
    @classmethod
    def validate_github_issue_or_pr_url(cls, value: HttpUrl) -> HttpUrl:
        text = str(value)
        if not re.search(r"github\.com/[^/]+/[^/]+/(issues|pull)/\d+", text):
            raise ValueError("Only GitHub issue and pull request URLs are supported.")
        return value


class WebhookSimulationRequest(BaseModel):
    event_type: Literal["issues", "pull_request"] = Field(default="issues", examples=["issues", "pull_request"])
    payload: Dict[str, Any]


class CiLogAnalyzeRequest(BaseModel):
    repo_full_name: str = Field(
        default="unknown/repo",
        min_length=3,
        max_length=120,
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        examples=["Fhonglei/sample-app"],
    )
    workflow_name: str = Field(default="CI", min_length=1, max_length=120, examples=["CI"])
    log_text: str = Field(min_length=20, max_length=20000)


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
