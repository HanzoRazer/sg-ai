# tests/test_sqlite_store.py
"""
Tests for SQLite session store.
"""

import pytest
from uuid import uuid4

from sg_engine.session.sqlite_store import SQLiteSessionStore


@pytest.fixture
def store():
    """Create an in-memory store for testing."""
    return SQLiteSessionStore(":memory:")


class TestSQLiteSessionStore:
    """Test suite for SQLite session store."""

    def test_create_session(self, store):
        """Can create a new session."""
        session_id = uuid4()
        session = store.create_session(
            session_id=session_id,
            device_id="device-001",
            context={"program": "test"},
        )

        assert session["session_id"] == session_id
        assert session["device_id"] == "device-001"
        assert session["context"] == {"program": "test"}
        assert session["active"] is True

    def test_get_session(self, store):
        """Can retrieve a created session."""
        session_id = uuid4()
        store.create_session(session_id=session_id, device_id="device-001")

        session = store.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id

    def test_get_session_not_found(self, store):
        """Returns None for non-existent session."""
        session = store.get_session(uuid4())
        assert session is None

    def test_get_active_session(self, store):
        """Can get the active session."""
        session_id = uuid4()
        store.create_session(session_id=session_id, device_id="device-001")

        active = store.get_active_session()
        assert active is not None
        assert active["session_id"] == session_id

    def test_active_session_changes(self, store):
        """Creating new session changes active session."""
        session1 = uuid4()
        session2 = uuid4()

        store.create_session(session_id=session1, device_id="device-001")
        store.create_session(session_id=session2, device_id="device-001")

        active = store.get_active_session()
        assert active["session_id"] == session2

    def test_add_events(self, store):
        """Can add events to a session."""
        session_id = uuid4()
        store.create_session(session_id=session_id, device_id="device-001")

        count = store.add_events(session_id, [
            {"type": "note", "pitch": 60},
            {"type": "note", "pitch": 62},
        ])

        assert count == 2

        # Verify events are stored
        session = store.get_session(session_id)
        assert len(session["events"]) == 2
        assert session["events"][0]["pitch"] == 60

    def test_add_events_to_nonexistent_session(self, store):
        """Adding events to non-existent session returns 0."""
        count = store.add_events(uuid4(), [{"type": "note"}])
        assert count == 0

    def test_set_feedback(self, store):
        """Can set feedback on a session."""
        session_id = uuid4()
        store.create_session(session_id=session_id, device_id="device-001")

        feedback = {"score": 85, "items": ["Good timing!"]}
        store.set_feedback(session_id, feedback)

        session = store.get_session(session_id)
        assert session["latest_feedback"] == feedback

    def test_stop_session(self, store):
        """Can stop a session."""
        session_id = uuid4()
        store.create_session(session_id=session_id, device_id="device-001")
        store.add_events(session_id, [{"type": "note"}] * 5)

        summary = store.stop_session(session_id)

        assert summary is not None
        assert summary["session_id"] == str(session_id)
        assert summary["event_count"] == 5
        assert summary["stopped_at"] is not None

        # Verify session is no longer active
        session = store.get_session(session_id)
        assert session["active"] is False

    def test_stop_clears_active_session(self, store):
        """Stopping active session clears active_session reference."""
        session_id = uuid4()
        store.create_session(session_id=session_id, device_id="device-001")
        store.stop_session(session_id)

        active = store.get_active_session()
        assert active is None

    def test_stop_nonexistent_session(self, store):
        """Stopping non-existent session returns None."""
        summary = store.stop_session(uuid4())
        assert summary is None

    def test_clear_all(self, store):
        """Can clear all sessions."""
        for _ in range(3):
            store.create_session(session_id=uuid4(), device_id="device-001")

        store.clear_all()

        assert store.get_active_session() is None
        # list_sessions should return empty
        sessions = store.list_sessions()
        assert len(sessions) == 0

    def test_list_sessions(self, store):
        """Can list all sessions."""
        for i in range(5):
            store.create_session(session_id=uuid4(), device_id=f"device-{i:03d}")

        sessions = store.list_sessions()
        assert len(sessions) == 5

    def test_list_sessions_by_device(self, store):
        """Can filter sessions by device."""
        for i in range(3):
            store.create_session(session_id=uuid4(), device_id="device-A")
        for i in range(2):
            store.create_session(session_id=uuid4(), device_id="device-B")

        sessions_a = store.list_sessions(device_id="device-A")
        assert len(sessions_a) == 3

        sessions_b = store.list_sessions(device_id="device-B")
        assert len(sessions_b) == 2

    def test_list_sessions_active_only(self, store):
        """Can filter to active sessions only."""
        id1 = uuid4()
        id2 = uuid4()
        store.create_session(session_id=id1, device_id="device-001")
        store.create_session(session_id=id2, device_id="device-001")
        store.stop_session(id1)

        active = store.list_sessions(active_only=True)
        assert len(active) == 1
        assert active[0]["session_id"] == id2

    def test_get_session_history(self, store):
        """Can get session history for practice_summary."""
        device_id = "device-001"

        # Create and stop some sessions
        for i in range(3):
            sid = uuid4()
            store.create_session(session_id=sid, device_id=device_id)
            store.add_events(sid, [{"type": "note"}] * (i + 1) * 10)
            store.stop_session(sid)

        history = store.get_session_history(device_id)
        assert len(history) == 3
        # All should be completed
        assert all(h["completed"] for h in history)
        # Should have event counts
        assert all("event_count" in h for h in history)

    def test_persistence_across_connections(self):
        """Data persists across store instances (file-based)."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            # Create session with first store
            store1 = SQLiteSessionStore(db_path)
            session_id = uuid4()
            store1.create_session(session_id=session_id, device_id="device-001")
            store1.add_events(session_id, [{"note": 60}])

            # Retrieve with second store instance
            store2 = SQLiteSessionStore(db_path)
            session = store2.get_session(session_id)

            assert session is not None
            assert session["device_id"] == "device-001"
            assert len(session["events"]) == 1
        finally:
            os.unlink(db_path)

    def test_context_json_serialization(self, store):
        """Complex context is properly serialized/deserialized."""
        session_id = uuid4()
        context = {
            "program": "test",
            "settings": {"tempo": 120, "grid": 16},
            "tags": ["practice", "timing"],
        }

        store.create_session(
            session_id=session_id,
            device_id="device-001",
            context=context,
        )

        session = store.get_session(session_id)
        assert session["context"] == context
        assert session["context"]["settings"]["tempo"] == 120
