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


def _safe_parse(source_url: str) -> tuple[Optional[str], Optional[str], str, Optional[int]]:
    from app.core.github_client import parse_github_url

    try:
        owner, repo, kind, number = parse_github_url(source_url)
        return owner, repo, kind, number
    except Exception:
        return None, None, "issue", None

