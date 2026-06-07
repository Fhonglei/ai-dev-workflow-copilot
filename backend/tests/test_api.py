from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_health_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "AI Dev Workflow Copilot"
    assert "llm_configured" in body


def test_analyze_rejects_non_github_url(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "invalid-url.db"))
    client = TestClient(app)

    response = client.post("/api/analyze", json={"source_url": "https://example.com/issues/1"})

    assert response.status_code == 422


def test_webhook_simulation_completes(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    from app.db.store import init_db

    init_db()
    client = TestClient(app)
    payload = {
        "action": "opened",
        "repository": {"full_name": "Fhonglei/sample"},
        "issue": {
            "number": 3,
            "title": "API returns exception on upload",
            "body": "Upload endpoint fails with an exception for large files.",
            "state": "open",
            "comments": 0,
            "html_url": "https://github.com/Fhonglei/sample/issues/3",
            "user": {"login": "tester"},
            "labels": [],
        },
    }
    response = client.post("/api/webhooks/simulate", json={"event_type": "issues", "payload": payload})
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    detail = client.get(f"/api/tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] in {"completed", "analyzing", "fetching_context", "received"}


def test_ci_log_sync_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "ci.db"))
    from app.db.store import init_db

    init_db()
    client = TestClient(app)
    response = client.post(
        "/api/analyze/ci-log/sync",
        json={
            "repo_full_name": "Fhonglei/sample",
            "workflow_name": "CI",
            "log_text": "Run pytest\nFAILED tests/test_api.py::test_login\nAssertionError: expected 200\nexit code 1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "ci_failure"
    assert body["status"] == "completed"
    assert body["analysis"]["category"] == "bug"
    assert "CI" in body["analysis"]["summary"]


def test_ci_log_rejects_invalid_repo_name(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "invalid-ci.db"))
    client = TestClient(app)

    response = client.post(
        "/api/analyze/ci-log/sync",
        json={
            "repo_full_name": "not a repo",
            "workflow_name": "CI",
            "log_text": "FAILED tests/test_api.py::test_login AssertionError expected 200 exit code 1",
        },
    )

    assert response.status_code == 422
