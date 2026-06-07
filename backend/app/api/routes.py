from typing import List

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.config import settings
from app.core.tasks import (
    create_ci_log_task,
    create_url_task,
    create_webhook_task,
    run_ci_log_analysis,
    run_url_analysis,
    run_webhook_analysis,
)
from app.core.webhook import verify_github_signature
from app.db.store import get_task, list_tasks
from app.models.schemas import (
    AnalyzeRequest,
    CiLogAnalyzeRequest,
    HealthOut,
    TaskCreated,
    TaskOut,
    WebhookSimulationRequest,
)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(
        status="healthy" if settings.llm_configured else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        llm_configured=settings.llm_configured,
        github_configured=settings.github_configured,
        webhook_secret_configured=bool(settings.github_webhook_secret),
    )


@router.post("/analyze", response_model=TaskCreated)
def analyze_issue_or_pr(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> TaskCreated:
    source_url = str(request.source_url)
    task_id = create_url_task(source_url)
    background_tasks.add_task(run_url_analysis, task_id, source_url, request.auto_comment, request.apply_labels)
    return TaskCreated(task_id=task_id, status="received")


@router.post("/analyze/sync", response_model=TaskOut)
async def analyze_issue_or_pr_sync(request: AnalyzeRequest) -> TaskOut:
    source_url = str(request.source_url)
    task_id = create_url_task(source_url)
    await run_url_analysis(task_id, source_url, request.auto_comment, request.apply_labels)
    task = get_task(task_id)
    assert task is not None
    return task


@router.post("/analyze/ci-log", response_model=TaskCreated)
def analyze_ci_log(request: CiLogAnalyzeRequest, background_tasks: BackgroundTasks) -> TaskCreated:
    task_id = create_ci_log_task(request.repo_full_name, request.workflow_name)
    background_tasks.add_task(run_ci_log_analysis, task_id, request.repo_full_name, request.workflow_name, request.log_text)
    return TaskCreated(task_id=task_id, status="received")


@router.post("/analyze/ci-log/sync", response_model=TaskOut)
async def analyze_ci_log_sync(request: CiLogAnalyzeRequest) -> TaskOut:
    task_id = create_ci_log_task(request.repo_full_name, request.workflow_name)
    await run_ci_log_analysis(task_id, request.repo_full_name, request.workflow_name, request.log_text)
    task = get_task(task_id)
    assert task is not None
    return task


@router.get("/tasks", response_model=List[TaskOut])
def tasks() -> List[TaskOut]:
    return list_tasks()


@router.get("/tasks/{task_id}", response_model=TaskOut)
def task_detail(task_id: str) -> TaskOut:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.post("/webhooks/simulate", response_model=TaskCreated)
def simulate_webhook(request: WebhookSimulationRequest, background_tasks: BackgroundTasks) -> TaskCreated:
    task_id = create_webhook_task(request.event_type, request.payload, simulation=True)
    background_tasks.add_task(run_webhook_analysis, task_id, request.event_type, request.payload)
    return TaskCreated(task_id=task_id, status="received")


@router.post("/webhooks/github", response_model=TaskCreated)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str | None = Header(default=None),
) -> TaskCreated:
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256, settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature.")
    payload = await request.json()
    supported = {"issues", "pull_request"}
    if x_github_event not in supported:
        raise HTTPException(status_code=202, detail=f"Ignored unsupported event: {x_github_event}")
    task_id = create_webhook_task(x_github_event, payload)
    background_tasks.add_task(run_webhook_analysis, task_id, x_github_event, payload)
    return TaskCreated(task_id=task_id, status="received")
