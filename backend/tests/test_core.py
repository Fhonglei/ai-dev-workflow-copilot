from app.core.analyzer import heuristic_analysis
from app.core.github_client import GitHubContext, parse_github_url
from app.core.webhook import verify_github_signature


def make_context(title: str = "Login fails with 500") -> GitHubContext:
    return GitHubContext(
        kind="issue",
        owner="Fhonglei",
        repo="sample",
        number=7,
        title=title,
        body="Users see an exception after password reset.",
        author="tester",
        state="open",
        labels=[],
        comments=1,
        repo_full_name="Fhonglei/sample",
        html_url="https://github.com/Fhonglei/sample/issues/7",
    )


def test_parse_github_issue_url():
    owner, repo, kind, number = parse_github_url("https://github.com/Fhonglei/sample/issues/42")
    assert owner == "Fhonglei"
    assert repo == "sample"
    assert kind == "issue"
    assert number == 42


def test_parse_github_pull_request_url():
    owner, repo, kind, number = parse_github_url("https://github.com/Fhonglei/sample/pull/9")
    assert owner == "Fhonglei"
    assert repo == "sample"
    assert kind == "pull_request"
    assert number == 9


def test_heuristic_analysis_for_bug():
    result = heuristic_analysis(make_context())
    assert result.category == "bug"
    assert result.priority in {"P1", "P2", "P3"}
    assert "bug" in result.suggested_labels
    assert result.action_plan
    assert result.test_plan


def test_verify_github_signature_without_secret_allows_request():
    assert verify_github_signature(b"{}", None, "") is True


def test_verify_github_signature_rejects_wrong_signature():
    assert verify_github_signature(b"{}", "sha256=bad", "secret") is False

