import json
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
    bug_score = _keyword_score(text, ["error", "bug", "crash", "fail", "exception", "broken", "regression"])
    docs_score = _keyword_score(text, ["readme", "docs", "documentation", "typo"])
    feature_score = _keyword_score(text, ["feature", "support", "add", "request", "enhancement"])

    if security_score:
        category = "security"
        priority = "P1"
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
        "ci": ["ci", "github actions", "workflow", "build", "test"],
        "docs": ["readme", "docs", "documentation"],
    }
    modules = [name for name, words in mapping.items() if any(word in text for word in words)]
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
            parsed: Dict[str, Any] = json.loads(content)
            return AnalysisResult.model_validate(parsed)
    except Exception:
        return heuristic_analysis(context)

