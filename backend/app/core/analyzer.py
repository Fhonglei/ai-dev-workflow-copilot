import json
import re
from typing import Any, Dict, List

import httpx

from app.config import settings
from app.core.github_client import GitHubContext
from app.models.schemas import AnalysisResult


def _keyword_score(text: str, keywords: List[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def heuristic_analysis(context: GitHubContext) -> AnalysisResult:
    text = f"{context.title}\n{context.body}".lower()
    security_score = _keyword_score(text, ["xss", "csrf", "auth", "token", "secret", "sql injection", "permission"])
    ci_score = _keyword_score(text, ["traceback", "assertionerror", "npm err", "pytest", "failed", "exit code", "build failed"])
    bug_score = _keyword_score(text, ["error", "bug", "crash", "fail", "exception", "broken", "regression"])
    docs_score = _keyword_score(text, ["readme", "docs", "documentation", "typo"])
    feature_score = _keyword_score(text, ["feature", "support", "add", "request", "enhancement"])

    if security_score:
        category = "security"
        priority = "P1"
    elif context.kind == "ci_failure" or ci_score >= 2:
        category = "bug"
        priority = "P1" if "production" in text or "deploy" in text else "P2"
    elif "production" in text or "urgent" in text or "data loss" in text:
        category = "bug"
        priority = "P0"
    elif bug_score:
        category = "bug"
        priority = "P2"
    elif docs_score:
        category = "docs"
        priority = "P3"
    elif feature_score:
        category = "feature"
        priority = "P3"
    elif context.kind == "pull_request":
        category = "refactor"
        priority = "P2"
    else:
        category = "triage"
        priority = "P3"

    modules = _guess_modules(context)
    labels = [category, priority.lower()]
    if context.kind == "ci_failure":
        labels.extend(["ci-failure", "needs-triage"])
        return _ci_failure_result(context, category, priority, modules, labels)
    if context.kind == "pull_request":
        labels.append("needs-review")
    else:
        labels.append("needs-triage")

    return AnalysisResult(
        category=category,
        priority=priority,
        confidence_score=72 if settings.llm_configured else 58,
        summary=f"{context.kind.replace('_', ' ').title()} #{context.number} in {context.repo_full_name} needs {category} triage. The likely scope is {', '.join(modules[:3])}.",
        suggested_labels=labels,
        impact_modules=modules,
        probable_causes=[
            "The report references behavior that is not covered by a visible acceptance test.",
            "The affected code path may be under-specified or missing validation around edge cases.",
            "Recent changes should be compared with the issue description and related CI signals.",
        ],
        action_plan=[
            "Reproduce the behavior locally or with a minimal request/example.",
            "Inspect the affected module and confirm expected behavior from README or API contracts.",
            "Implement the smallest focused fix and keep unrelated refactors out of scope.",
            "Add regression coverage for the exact failure mode before closing the task.",
        ],
        test_plan=[
            "Add or update a unit test for the impacted module.",
            "Add an API/integration test if the behavior crosses service boundaries.",
            "Run lint, typecheck, and the relevant backend/frontend test suite.",
        ],
        acceptance_criteria=[
            "The issue or PR has a clear category, priority, owner-facing summary, and labels.",
            "The proposed fix path includes reproducible steps and regression tests.",
            "The maintainer can decide next action without re-reading the full thread.",
        ],
        review_checklist=[
            "Does the change address the reported behavior without broad side effects?",
            "Are error states and edge cases covered?",
            "Is the test plan specific enough to catch regressions?",
            "Are user-visible messages and documentation updated if behavior changed?",
        ],
        maintainer_comment=_maintainer_comment(context, category, priority, modules),
        risks=[
            "AI triage can misclassify underspecified reports; maintainers should review before applying labels.",
            "Automated comments should be disabled for private or sensitive repositories until webhook permissions are audited.",
        ],
    )


def _ci_failure_result(
    context: GitHubContext,
    category: str,
    priority: str,
    modules: List[str],
    labels: List[str],
) -> AnalysisResult:
    return AnalysisResult(
        category=category,
        priority=priority,
        confidence_score=75 if settings.llm_configured else 62,
        summary=(
            f"CI workflow `{context.title}` failed in {context.repo_full_name}. "
            f"The failure should be treated as `{category}` with priority `{priority}` because it blocks validation "
            f"for {', '.join(modules[:3])}."
        ),
        suggested_labels=labels,
        impact_modules=modules,
        probable_causes=[
            "A test assertion, build command, or dependency step failed in the CI job log.",
            "The failing path is likely close to the test file, package command, or stack trace shown in the excerpt.",
            "The pipeline may be missing a reproducible local command that developers can run before pushing.",
        ],
        action_plan=[
            "Identify the first failing command and keep later cascading errors as secondary signals.",
            "Reproduce the same command locally with the same runtime and environment variables.",
            "Inspect the module named by the failing test, stack trace, or package manager output.",
            "Fix the root cause, then rerun the specific failing test before rerunning the full CI suite.",
        ],
        test_plan=[
            "Add or update a regression test for the failing assertion or command.",
            "Run the exact failing CI command locally.",
            "Run the full backend/frontend quality gate before merging.",
        ],
        acceptance_criteria=[
            "The failing CI command passes locally and in GitHub Actions.",
            "The root cause is documented in the PR or issue comment.",
            "A focused regression test covers the failure mode when applicable.",
        ],
        review_checklist=[
            "Does the fix address the first failing CI signal instead of only a downstream symptom?",
            "Are environment assumptions such as secrets, paths, versions, and service availability explicit?",
            "Did the author rerun the narrow failing command and the full quality gate?",
        ],
        maintainer_comment=(
            f"AI CI triage: `{context.title}` is classified as `{category}` / `{priority}`. "
            f"Likely affected area: {', '.join(modules)}. Start with the first failing command in the log, "
            "reproduce it locally, then add or update regression coverage before merging."
        ),
        risks=[
            "A truncated CI log can hide the first root-cause failure.",
            "Missing secrets or network-only dependencies can make local reproduction differ from GitHub Actions.",
        ],
    )


def _guess_modules(context: GitHubContext) -> List[str]:
    if context.changed_files:
        modules = []
        for item in context.changed_files:
            filename = item.get("filename") or ""
            if "/" in filename:
                modules.append(filename.split("/", 1)[0])
            elif filename:
                modules.append(filename)
        unique = []
        for module in modules:
            if module not in unique:
                unique.append(module)
        return unique[:6] or ["application"]
    text = f"{context.title} {context.body}".lower()
    mapping = {
        "frontend": ["frontend", "ui", "page", "button", "react", "next"],
        "backend": ["api", "fastapi", "server", "endpoint", "database"],
        "auth": ["login", "auth", "token", "permission", "session"],
        "ci": ["ci", "github actions", "workflow", "build", "test", "pytest", "assertionerror", "exit code"],
        "files": ["upload", "file", "blob", "storage"],
        "dependencies": ["npm", "pip", "package", "dependency", "lockfile"],
        "docs": ["readme", "docs", "documentation"],
    }
    modules = [name for name, words in mapping.items() if any(word in text for word in words)]
    if context.kind == "ci_failure" and "ci" not in modules:
        modules.insert(0, "ci")
    return modules or ["application"]


def _maintainer_comment(context: GitHubContext, category: str, priority: str, modules: List[str]) -> str:
    return (
        f"AI triage summary for {context.kind.replace('_', ' ')} #{context.number}: "
        f"classified as `{category}` with priority `{priority}`. "
        f"Likely affected area: {', '.join(modules)}. "
        "Recommended next step: reproduce or inspect the touched code path, then add focused regression coverage before closing."
    )


def _analysis_schema_hint() -> str:
    return json.dumps(
        {
            "category": "bug | feature | docs | refactor | security | triage",
            "priority": "P0 | P1 | P2 | P3",
            "confidence_score": 0,
            "summary": "...",
            "suggested_labels": ["bug", "p2"],
            "impact_modules": ["backend"],
            "probable_causes": ["..."],
            "action_plan": ["..."],
            "test_plan": ["..."],
            "acceptance_criteria": ["..."],
            "review_checklist": ["..."],
            "maintainer_comment": "...",
            "risks": ["..."],
        },
        ensure_ascii=False,
    )


def parse_llm_json(content: str) -> Dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


async def analyze_with_llm(context: GitHubContext) -> AnalysisResult:
    if not settings.llm_configured:
        return heuristic_analysis(context)
    prompt = (
        "You are an experienced software engineering triage assistant. "
        "Analyze the GitHub issue or pull request context and return strict JSON only. "
        "Do not include markdown fences. Schema: "
        f"{_analysis_schema_hint()}\n\nContext:\n"
        f"{json.dumps(context.to_prompt_context(), ensure_ascii=False)}"
    )
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": "Return strict JSON that matches the requested schema."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed: Dict[str, Any] = parse_llm_json(content)
            return AnalysisResult.model_validate(parsed)
    except Exception:
        return heuristic_analysis(context)
