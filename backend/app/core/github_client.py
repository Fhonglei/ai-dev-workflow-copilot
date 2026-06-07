import base64
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

GITHUB_API = "https://api.github.com"


class GitHubClientError(RuntimeError):
    pass


@dataclass
class GitHubContext:
    kind: str
    owner: str
    repo: str
    number: int
    title: str
    body: str
    author: str
    state: str
    labels: List[str]
    comments: int
    repo_full_name: str
    html_url: str
    readme_excerpt: str = ""
    changed_files: List[Dict[str, Any]] | None = None
    ci_summary: List[Dict[str, Any]] | None = None

    def to_prompt_context(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "repo": self.repo_full_name,
            "number": self.number,
            "title": self.title,
            "body": self.body[:5000],
            "author": self.author,
            "state": self.state,
            "labels": self.labels,
            "comments": self.comments,
            "readme_excerpt": self.readme_excerpt[:3000],
            "changed_files": self.changed_files or [],
            "ci_summary": self.ci_summary or [],
        }


def parse_github_url(url: str) -> tuple[str, str, str, int]:
    match = re.search(r"github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)", url)
    if not match:
        raise GitHubClientError("Only GitHub issue and pull request URLs are supported.")
    owner, repo, kind, number = match.groups()
    return owner, repo.removesuffix(".git"), "pull_request" if kind == "pull" else "issue", int(number)


def _headers(accept: str = "application/vnd.github+json") -> Dict[str, str]:
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-dev-workflow-copilot",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _get_json(client: httpx.Client, path: str) -> Dict[str, Any] | List[Any]:
    response = client.get(f"{GITHUB_API}{path}", headers=_headers())
    if response.status_code >= 400:
        raise GitHubClientError(f"GitHub API returned {response.status_code} for {path}.")
    return response.json()


def _get_readme_excerpt(client: httpx.Client, owner: str, repo: str) -> str:
    response = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/readme", headers=_headers())
    if response.status_code >= 400:
        return ""
    payload = response.json()
    content = payload.get("content") or ""
    if not content:
        return ""
    try:
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return ""
    return decoded[:3000]


def fetch_context_from_url(url: str) -> GitHubContext:
    owner, repo, kind, number = parse_github_url(url)
    with httpx.Client(timeout=20) as client:
        readme = _get_readme_excerpt(client, owner, repo)
        if kind == "issue":
            issue = _get_json(client, f"/repos/{owner}/{repo}/issues/{number}")
            if "pull_request" in issue:
                return _fetch_pr_context(client, owner, repo, number, readme)
            return GitHubContext(
                kind="issue",
                owner=owner,
                repo=repo,
                number=number,
                title=issue.get("title") or "",
                body=issue.get("body") or "",
                author=(issue.get("user") or {}).get("login") or "unknown",
                state=issue.get("state") or "unknown",
                labels=[label.get("name", "") for label in issue.get("labels", [])],
                comments=int(issue.get("comments") or 0),
                repo_full_name=f"{owner}/{repo}",
                html_url=issue.get("html_url") or url,
                readme_excerpt=readme,
            )
        return _fetch_pr_context(client, owner, repo, number, readme)


def _fetch_pr_context(client: httpx.Client, owner: str, repo: str, number: int, readme: str) -> GitHubContext:
    pr = _get_json(client, f"/repos/{owner}/{repo}/pulls/{number}")
    files = _get_json(client, f"/repos/{owner}/{repo}/pulls/{number}/files")
    changed_files = [
        {
            "filename": item.get("filename"),
            "status": item.get("status"),
            "additions": item.get("additions"),
            "deletions": item.get("deletions"),
            "patch_excerpt": (item.get("patch") or "")[:1200],
        }
        for item in files[:20]
    ]
    ci_summary: List[Dict[str, Any]] = []
    sha = (pr.get("head") or {}).get("sha")
    if sha:
        checks = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/commits/{sha}/check-runs", headers=_headers())
        if checks.status_code < 400:
            payload = checks.json()
            ci_summary = [
                {
                    "name": run.get("name"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "details_url": run.get("details_url"),
                }
                for run in payload.get("check_runs", [])[:10]
            ]
    return GitHubContext(
        kind="pull_request",
        owner=owner,
        repo=repo,
        number=number,
        title=pr.get("title") or "",
        body=pr.get("body") or "",
        author=((pr.get("user") or {}).get("login")) or "unknown",
        state=pr.get("state") or "unknown",
        labels=[],
        comments=int(pr.get("comments") or 0),
        repo_full_name=f"{owner}/{repo}",
        html_url=pr.get("html_url") or f"https://github.com/{owner}/{repo}/pull/{number}",
        readme_excerpt=readme,
        changed_files=changed_files,
        ci_summary=ci_summary,
    )


def context_from_webhook(event_type: str, payload: Dict[str, Any]) -> Optional[GitHubContext]:
    repo = payload.get("repository") or {}
    repo_full_name = repo.get("full_name") or "unknown/repo"
    if "/" in repo_full_name:
        owner, repo_name = repo_full_name.split("/", 1)
    else:
        owner, repo_name = "unknown", repo_full_name
    if event_type == "issues" and payload.get("issue"):
        issue = payload["issue"]
        return GitHubContext(
            kind="issue",
            owner=owner,
            repo=repo_name,
            number=int(issue.get("number") or 0),
            title=issue.get("title") or "",
            body=issue.get("body") or "",
            author=((issue.get("user") or {}).get("login")) or "unknown",
            state=issue.get("state") or "unknown",
            labels=[label.get("name", "") for label in issue.get("labels", [])],
            comments=int(issue.get("comments") or 0),
            repo_full_name=repo_full_name,
            html_url=issue.get("html_url") or "",
        )
    if event_type == "pull_request" and payload.get("pull_request"):
        pr = payload["pull_request"]
        return GitHubContext(
            kind="pull_request",
            owner=owner,
            repo=repo_name,
            number=int(pr.get("number") or 0),
            title=pr.get("title") or "",
            body=pr.get("body") or "",
            author=((pr.get("user") or {}).get("login")) or "unknown",
            state=pr.get("state") or "unknown",
            labels=[],
            comments=int(pr.get("comments") or 0),
            repo_full_name=repo_full_name,
            html_url=pr.get("html_url") or "",
            changed_files=[],
            ci_summary=[],
        )
    return None


def post_issue_comment(context: GitHubContext, body: str) -> Dict[str, Any]:
    if not settings.github_token:
        return {"skipped": True, "reason": "GITHUB_TOKEN is not configured."}
    with httpx.Client(timeout=20) as client:
        response = client.post(
            f"{GITHUB_API}/repos/{context.owner}/{context.repo}/issues/{context.number}/comments",
            headers=_headers(),
            json={"body": body},
        )
        if response.status_code >= 400:
            return {"skipped": False, "ok": False, "status_code": response.status_code}
        return {"skipped": False, "ok": True, "comment_url": response.json().get("html_url")}


def apply_issue_labels(context: GitHubContext, labels: List[str]) -> Dict[str, Any]:
    if not settings.github_token:
        return {"skipped": True, "reason": "GITHUB_TOKEN is not configured."}
    with httpx.Client(timeout=20) as client:
        response = client.post(
            f"{GITHUB_API}/repos/{context.owner}/{context.repo}/issues/{context.number}/labels",
            headers=_headers(),
            json={"labels": labels[:5]},
        )
        if response.status_code >= 400:
            return {"skipped": False, "ok": False, "status_code": response.status_code}
        return {"skipped": False, "ok": True, "labels": labels[:5]}

