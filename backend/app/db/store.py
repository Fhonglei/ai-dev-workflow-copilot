import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models.schemas import AnalysisResult, TaskOut

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    db_path = settings.db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              status TEXT NOT NULL,
              source_url TEXT,
              repo_full_name TEXT,
              number INTEGER,
              title TEXT,
              analysis_json TEXT,
              automation_json TEXT,
              error TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def create_task(task_id: str, kind: str, source_url: Optional[str] = None) -> TaskOut:
    now = _now()
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, kind, status, source_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, kind, "received", source_url, now, now),
        )
        conn.commit()
    task = get_task(task_id)
    assert task is not None
    return task


def update_task(task_id: str, **updates: Any) -> None:
    if not updates:
        return
    updates["updated_at"] = _now()
    columns = []
    values = []
    for key, value in updates.items():
        if key == "analysis":
            key = "analysis_json"
            value = json.dumps(value, ensure_ascii=False)
        elif key == "automation_result":
            key = "automation_json"
            value = json.dumps(value, ensure_ascii=False)
        columns.append(f"{key} = ?")
        values.append(value)
    values.append(task_id)
    with _lock, _connect() as conn:
        conn.execute(f"UPDATE tasks SET {', '.join(columns)} WHERE id = ?", values)
        conn.commit()


def _row_to_task(row: sqlite3.Row) -> TaskOut:
    analysis = None
    if row["analysis_json"]:
        analysis = AnalysisResult.model_validate(json.loads(row["analysis_json"]))
    automation = json.loads(row["automation_json"]) if row["automation_json"] else None
    return TaskOut(
        id=row["id"],
        kind=row["kind"],
        status=row["status"],
        source_url=row["source_url"],
        repo_full_name=row["repo_full_name"],
        number=row["number"],
        title=row["title"],
        analysis=analysis,
        automation_result=automation,
        error=row["error"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def get_task(task_id: str) -> Optional[TaskOut]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def list_tasks(limit: int = 50) -> List[TaskOut]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_task(row) for row in rows]

