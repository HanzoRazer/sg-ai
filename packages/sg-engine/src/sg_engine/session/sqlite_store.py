"""
SQLite Session Store — persistent session management.

Device-local identity model: sessions keyed by UUID, stored in SQLite.
Survives process restarts. Thread-safe via SQLite's built-in locking.

Usage:
    store = SQLiteSessionStore("sessions.db")
    store.create_session(session_id=uuid, device_id="device-001")
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator
from uuid import UUID


class SQLiteSessionStore:
    """
    SQLite-backed session store.

    Thread-safe through SQLite's internal locking.
    For file-based databases: connection per operation.
    For :memory: databases: persistent connection (required for schema to persist).
    """

    def __init__(self, db_path: str | Path = "sessions.db"):
        """
        Initialize the SQLite session store.

        Args:
            db_path: Path to the SQLite database file.
                     Use ":memory:" for in-memory (testing).
        """
        self._db_path = str(db_path)
        self._is_memory = self._db_path == ":memory:"
        self._persistent_conn: sqlite3.Connection | None = None

        if self._is_memory:
            # For in-memory DB, keep a persistent connection
            self._persistent_conn = sqlite3.connect(":memory:")
            self._persistent_conn.row_factory = sqlite3.Row

        self._init_schema()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        if self._is_memory and self._persistent_conn:
            # Use persistent connection for in-memory DB
            yield self._persistent_conn
            self._persistent_conn.commit()
        else:
            # Create new connection for file-based DB
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    context_json TEXT DEFAULT '{}',
                    started_at TEXT NOT NULL,
                    stopped_at TEXT,
                    latest_feedback_json TEXT,
                    active INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_events_session
                ON session_events(session_id);

                CREATE TABLE IF NOT EXISTS active_session (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    session_id TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                INSERT OR IGNORE INTO active_session (id, session_id) VALUES (1, NULL);
            """)

    def create_session(
        self,
        *,
        session_id: UUID,
        device_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new session."""
        started_at = datetime.now(timezone.utc).isoformat()
        session_id_str = str(session_id)
        context_json = json.dumps(context or {})

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, device_id, context_json, started_at, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (session_id_str, device_id, context_json, started_at),
            )
            # Set as active session
            conn.execute(
                "UPDATE active_session SET session_id = ? WHERE id = 1",
                (session_id_str,),
            )

        return {
            "session_id": session_id,
            "device_id": device_id,
            "context": context or {},
            "started_at": started_at,
            "stopped_at": None,
            "events": [],
            "latest_feedback": None,
            "active": True,
        }

    def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Get a session by ID."""
        session_id_str = str(session_id)

        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id_str,),
            ).fetchone()

            if row is None:
                return None

            # Get events
            events = conn.execute(
                "SELECT event_json FROM session_events WHERE session_id = ? ORDER BY id",
                (session_id_str,),
            ).fetchall()

        return {
            "session_id": UUID(row["session_id"]),
            "device_id": row["device_id"],
            "context": json.loads(row["context_json"]),
            "started_at": row["started_at"],
            "stopped_at": row["stopped_at"],
            "events": [json.loads(e["event_json"]) for e in events],
            "latest_feedback": json.loads(row["latest_feedback_json"]) if row["latest_feedback_json"] else None,
            "active": bool(row["active"]),
        }

    def get_active_session(self) -> dict[str, Any] | None:
        """Get the currently active session."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT session_id FROM active_session WHERE id = 1",
            ).fetchone()

            if row is None or row["session_id"] is None:
                return None

            session_id_str = row["session_id"]

        session = self.get_session(UUID(session_id_str))
        if session and session.get("active"):
            return session
        return None

    def add_events(self, session_id: UUID, events: list[dict[str, Any]]) -> int:
        """Add events to a session. Returns total event count."""
        session_id_str = str(session_id)
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connection() as conn:
            # Verify session exists
            row = conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (session_id_str,),
            ).fetchone()

            if row is None:
                return 0

            # Insert events
            for event in events:
                conn.execute(
                    """
                    INSERT INTO session_events (session_id, event_json, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (session_id_str, json.dumps(event), created_at),
                )

            # Get total count
            count_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM session_events WHERE session_id = ?",
                (session_id_str,),
            ).fetchone()

        return count_row["cnt"] if count_row else 0

    def set_feedback(self, session_id: UUID, feedback: dict[str, Any]) -> None:
        """Set the latest feedback for a session."""
        session_id_str = str(session_id)
        feedback_json = json.dumps(feedback)

        with self._connection() as conn:
            conn.execute(
                "UPDATE sessions SET latest_feedback_json = ? WHERE session_id = ?",
                (feedback_json, session_id_str),
            )

    def stop_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Stop a session and return summary."""
        session_id_str = str(session_id)
        stopped_at = datetime.now(timezone.utc).isoformat()

        with self._connection() as conn:
            # Get session info first
            row = conn.execute(
                "SELECT device_id, started_at FROM sessions WHERE session_id = ?",
                (session_id_str,),
            ).fetchone()

            if row is None:
                return None

            # Update session
            conn.execute(
                "UPDATE sessions SET stopped_at = ?, active = 0 WHERE session_id = ?",
                (stopped_at, session_id_str),
            )

            # Clear active session if it was this one
            conn.execute(
                "UPDATE active_session SET session_id = NULL WHERE id = 1 AND session_id = ?",
                (session_id_str,),
            )

            # Get event count
            count_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM session_events WHERE session_id = ?",
                (session_id_str,),
            ).fetchone()

        return {
            "session_id": session_id_str,
            "device_id": row["device_id"],
            "started_at": row["started_at"],
            "stopped_at": stopped_at,
            "event_count": count_row["cnt"] if count_row else 0,
        }

    def clear_all(self) -> None:
        """Clear all sessions (for testing)."""
        with self._connection() as conn:
            conn.execute("DELETE FROM session_events")
            conn.execute("DELETE FROM sessions")
            conn.execute("UPDATE active_session SET session_id = NULL WHERE id = 1")

    def list_sessions(
        self,
        *,
        device_id: str | None = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions with optional filters."""
        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []

        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)

        if active_only:
            query += " AND active = 1"

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "session_id": UUID(row["session_id"]),
                "device_id": row["device_id"],
                "started_at": row["started_at"],
                "stopped_at": row["stopped_at"],
                "active": bool(row["active"]),
            }
            for row in rows
        ]

    def get_session_history(
        self,
        device_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent session history for a device (for practice_summary)."""
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT s.session_id, s.started_at, s.stopped_at,
                       (SELECT COUNT(*) FROM session_events WHERE session_id = s.session_id) as event_count
                FROM sessions s
                WHERE s.device_id = ? AND s.stopped_at IS NOT NULL
                ORDER BY s.started_at DESC
                LIMIT ?
                """,
                (device_id, limit),
            ).fetchall()

        history = []
        for row in rows:
            started = datetime.fromisoformat(row["started_at"])
            stopped = datetime.fromisoformat(row["stopped_at"]) if row["stopped_at"] else started
            duration = (stopped - started).total_seconds()
            history.append({
                "session_id": row["session_id"],
                "duration_seconds": int(duration),
                "event_count": row["event_count"],
                "completed": True,
            })

        return history
