import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.analyzer import heuristic_analysis
from app.core.github_client import GitHubContext

DATASET = ROOT / "evals" / "triage_cases.jsonl"
REPORT = ROOT / "evals" / "last_run.json"
MIN_ACCURACY = 0.8


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def to_context(case: dict) -> GitHubContext:
    owner, repo = case["repo"].split("/", 1)
    return GitHubContext(
        kind=case["kind"],
        owner=owner,
        repo=repo,
        number=case["number"],
        title=case["title"],
        body=case["body"],
        author="eval",
        state="open",
        labels=[],
        comments=0,
        repo_full_name=case["repo"],
        html_url=f"https://github.com/{case['repo']}/issues/{case['number']}",
    )


def main() -> None:
    cases = load_cases()
    if not cases:
        raise RuntimeError(f"No evaluation cases found in {DATASET}.")
    rows = []
    category_hits = 0
    priority_hits = 0
    for case in cases:
        result = heuristic_analysis(to_context(case))
        category_ok = result.category == case["expected_category"]
        priority_ok = result.priority == case["expected_priority"]
        category_hits += int(category_ok)
        priority_hits += int(priority_ok)
        rows.append(
            {
                "title": case["title"],
                "expected_category": case["expected_category"],
                "actual_category": result.category,
                "category_ok": category_ok,
                "expected_priority": case["expected_priority"],
                "actual_priority": result.priority,
                "priority_ok": priority_ok,
            }
        )
    report = {
        "case_count": len(cases),
        "category_accuracy": round(category_hits / len(cases), 3),
        "priority_accuracy": round(priority_hits / len(cases), 3),
        "cases": rows,
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["category_accuracy"] < MIN_ACCURACY or report["priority_accuracy"] < MIN_ACCURACY:
        print(f"Evaluation accuracy is below the required threshold of {MIN_ACCURACY}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
