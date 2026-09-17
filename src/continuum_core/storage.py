from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS self_model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    author TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    model_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model_name TEXT,
                    content TEXT NOT NULL
                );
                """
            )

    def get_state(self, key: str, default: Any = None) -> Any:
        with self.connect() as db:
            row = db.execute("SELECT value_json FROM state WHERE key = ?", (key,)).fetchone()
        return default if row is None else json.loads(row["value_json"])

    def set_state(self, key: str, value: Any) -> None:
        payload = json.dumps(value, sort_keys=True)
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO state(key, value_json, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, payload, utc_now()),
            )

    def add_event(self, kind: str, content: str, source: str = "human") -> int:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO events(created_at, kind, source, content) VALUES (?, ?, ?, ?)",
                (utc_now(), kind, source, content),
            )
            return int(cursor.lastrowid)

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def add_self_model(self, model: dict[str, Any], author: str, reason: str) -> int:
        with self.connect() as db:
            cursor = db.execute(
                """
                INSERT INTO self_model_versions(created_at, author, reason, model_json)
                VALUES (?, ?, ?, ?)
                """,
                (utc_now(), author, reason, json.dumps(model, sort_keys=True)),
            )
            return int(cursor.lastrowid)

    def current_self_model(self) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT model_json FROM self_model_versions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return None if row is None else json.loads(row["model_json"])

    def add_reflection(self, content: str, mode: str, model_name: str | None = None) -> int:
        with self.connect() as db:
            cursor = db.execute(
                """
                INSERT INTO reflections(created_at, mode, model_name, content)
                VALUES (?, ?, ?, ?)
                """,
                (utc_now(), mode, model_name, content),
            )
            return int(cursor.lastrowid)

    def recent_reflections(self, limit: int = 10) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM reflections ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def snapshot(self) -> dict[str, Any]:
        return {
            "database": str(self.path),
            "state": {
                key: self.get_state(key)
                for key in (
                    "created_at",
                    "last_tick_at",
                    "tick_count",
                    "seconds_since_previous_tick",
                    "unresolved_questions",
                )
            },
            "self_model": self.current_self_model(),
            "events": self.recent_events(limit=100),
            "reflections": self.recent_reflections(limit=100),
            "exported_at": utc_now(),
        }

