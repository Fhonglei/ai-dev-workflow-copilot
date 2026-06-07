import asyncio
import uuid
from typing import Optional

from app.core.analyzer import analyze_with_llm
from app.core.github_client import (
    GitHubContext,
    apply_issue_labels,
    context_from_webhook,
    fetch_context_from_url,
    post_issue_comment,
)
from app.db.store import create_task, update_task


def new_task_id() -> str:
    return str(uuid.uuid4())


async def run_url_analysis(task_id: str, source_url: str, auto_comment: bool, apply_labels: bool) -> None:
    try:
        update_task(task_id, status="fetching_context")
        context = fetch_context_from_url(source_url)
        update_task(
            task_id,
            repo_full_name=context.repo_full_name,
            number=context.number,
            title=context.title,
        )
        await _analyze_and_optionally_act(task_id, context, auto_comment, apply_labels)
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))


async def run_webhook_analysis(
    task_id: str,
    event_type: str,
    payload: dict,
    auto_comment: bool = False,
    apply_labels: bool = False,
) -> None:
    try:
        update_task(task_id, status="fetching_context")
        context = context_from_webhook(event_type, payload)
        if context is None:
            raise ValueError(f"Unsupported webhook event: {event_type}")
        update_task(
            task_id,
            source_url=context.html_url,
            repo_full_name=context.repo_full_name,
            number=context.number,
            title=context.title,
        )
        await _analyze_and_optionally_act(task_id, context, auto_comment, apply_labels)
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))


async def run_ci_log_analysis(task_id: str, repo_full_name: str, workflow_name: str, log_text: str) -> None:
    try:
        update_task(task_id, status="fetching_context", repo_full_name=repo_full_name, title=workflow_name)
        context = GitHubContext(
            kind="ci_failure",
            owner=repo_full_name.split("/", 1)[0] if "/" in repo_full_name else "unknown",
            repo=repo_full_name.split("/", 1)[1] if "/" in repo_full_name else repo_full_name,
            number=0,
            title=f"{workflow_name} failure",
            body=_summarize_ci_log(log_text),
            author="ci",
            state="failed",
            labels=[],
            comments=0,
            repo_full_name=repo_full_name,
            html_url="",
            ci_summary=[{"name": workflow_name, "status": "completed", "conclusion": "failure"}],
        )
        await _analyze_and_optionally_act(task_id, context, auto_comment=False, apply_labels=False)
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))


async def _analyze_and_optionally_act(
    task_id: str,
    context: GitHubContext,
    auto_comment: bool,
    apply_labels: bool,
) -> None:
    update_task(task_id, status="analyzing")
    analysis = await analyze_with_llm(context)
    automation = {
        "comment": {"skipped": True, "reason": "auto_comment=false"},
        "labels": {"skipped": True, "reason": "apply_labels=false"},
    }
    if auto_comment:
        automation["comment"] = await asyncio.to_thread(post_issue_comment, context, analysis.maintainer_comment)
    if apply_labels:
        automation["labels"] = await asyncio.to_thread(apply_issue_labels, context, analysis.suggested_labels)
    update_task(
        task_id,
        status="completed",
        analysis=analysis.model_dump(),
        automation_result=automation,
    )


def create_url_task(source_url: str) -> str:
    task_id = new_task_id()
    owner, repo, kind, _ = _safe_parse(source_url)
    create_task(task_id, kind=kind, source_url=source_url)
    if owner and repo:
        update_task(task_id, repo_full_name=f"{owner}/{repo}")
    return task_id


def create_webhook_task(event_type: str, payload: dict, simulation: bool = False) -> str:
    task_id = new_task_id()
    kind = "webhook_simulation" if simulation else ("pull_request" if event_type == "pull_request" else "issue")
    create_task(task_id, kind=kind)
    context = context_from_webhook(event_type, payload)
    if context:
        update_task(
            task_id,
            source_url=context.html_url,
            repo_full_name=context.repo_full_name,
            number=context.number,
            title=context.title,
        )
    return task_id


def create_ci_log_task(repo_full_name: str, workflow_name: str) -> str:
    task_id = new_task_id()
    create_task(task_id, kind="ci_failure")
    update_task(task_id, repo_full_name=repo_full_name, title=f"{workflow_name} failure")
    return task_id


def _summarize_ci_log(log_text: str) -> str:
    interesting = []
    for line in log_text.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in ["error", "failed", "traceback", "assert", "exit code", "npm err", "pytest"]):
            interesting.append(line.strip())
    excerpt = "\n".join(interesting[:40]) or log_text[:4000]
    return f"CI failure log excerpt:\n{excerpt[:6000]}"


def _safe_parse(source_url: str) -> tuple[Optional[str], Optional[str], str, Optional[int]]:
    from app.core.github_client import parse_github_url

    try:
        owner, repo, kind, number = parse_github_url(source_url)
        return owner, repo, kind, number
    except Exception:
        return None, None, "issue", None
