"""
Session Store — in-memory session management.

Device-local identity model: sessions keyed by UUID.
No persistence in v0 — sessions lost on restart.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID


class SessionStore:
    """
    In-memory session store.

    Thread-safe for single-process use (GIL protected).
    For multi-process, use Redis or similar.
    """

    def __init__(self):
        self._sessions: dict[UUID, dict[str, Any]] = {}
        self._active_session_id: UUID | None = None

    def create_session(
        self,
        *,
        session_id: UUID,
        device_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new session."""
        session = {
            "session_id": session_id,
            "device_id": device_id,
            "context": context or {},
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stopped_at": None,
            "events": [],
            "latest_feedback": None,
            "active": True,
        }
        self._sessions[session_id] = session
        self._active_session_id = session_id
        return session

    def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_active_session(self) -> dict[str, Any] | None:
        """Get the currently active session."""
        if self._active_session_id is None:
            return None
        session = self._sessions.get(self._active_session_id)
        if session and session.get("active"):
            return session
        return None

    def add_events(self, session_id: UUID, events: list[dict[str, Any]]) -> int:
        """Add events to a session. Returns total event count."""
        session = self._sessions.get(session_id)
        if session is None:
            return 0
        session["events"].extend(events)
        return len(session["events"])

    def set_feedback(self, session_id: UUID, feedback: dict[str, Any]) -> None:
        """Set the latest feedback for a session."""
        session = self._sessions.get(session_id)
        if session:
            session["latest_feedback"] = feedback

    def stop_session(self, session_id: UUID) -> dict[str, Any] | None:
        """
        Stop a session and return summary.

        Returns None if session not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        session["stopped_at"] = datetime.now(timezone.utc).isoformat()
        session["active"] = False

        if self._active_session_id == session_id:
            self._active_session_id = None

        # Generate summary
        summary = {
            "session_id": str(session_id),
            "device_id": session["device_id"],
            "started_at": session["started_at"],
            "stopped_at": session["stopped_at"],
            "event_count": len(session["events"]),
        }
        return summary

    def clear_all(self) -> None:
        """Clear all sessions (for testing)."""
        self._sessions.clear()
        self._active_session_id = None
