# tests/test_practice_summary.py
"""
Tests for practice_summary job.
"""

import pytest
from sg_engine.jobs.practice_summary import run_job, run_practice_summary


def _make_context(
    duration_seconds: int = 600,
    notes_played: int = 200,
    session_history: list = None,
):
    """Build a valid practice_summary context."""
    return {
        "request": {
            "template_id": "practice_summary",
            "template_version": "1.0.0",
            "kind": "practice_summary",
        },
        "evidence": {
            "session_stats": {
                "duration_seconds": duration_seconds,
                "notes_played": notes_played,
                "bars_completed": 32,
            },
            "session_history": session_history or [],
            "groove_metrics": {
                "tempo_stability": 0.7,
            },
        },
    }


class TestPracticeSummaryJob:
    """Test suite for practice_summary job."""

    def test_basic_summary_generated(self):
        """Basic summary is generated with feedback items."""
        context = _make_context()
        draft = run_job(context)

        assert draft["schema_id"] == "coaching_draft_v1"
        assert draft["kind"] == "practice_summary"
        assert "feedback" in draft
        assert len(draft["feedback"]) >= 1

    def test_long_session_praised(self):
        """Sessions over 30 minutes get recognition."""
        context = _make_context(duration_seconds=1900)  # ~32 minutes
        draft = run_job(context)

        # Should have strength feedback about duration
        strengths = [f for f in draft["feedback"] if f["category"] == "strength"]
        assert len(strengths) >= 1
        duration_feedback = [s for s in strengths if "duration_seconds" in str(s["evidence_refs"])]
        assert len(duration_feedback) >= 1

    def test_short_session_gets_tip(self):
        """Short sessions get tips to extend."""
        context = _make_context(duration_seconds=300)  # 5 minutes
        draft = run_job(context)

        # Should have tip about extending practice
        tips = [f for f in draft["feedback"] if f["category"] == "tip"]
        assert len(tips) >= 1

    def test_high_activity_praised(self):
        """High note count gets recognition."""
        context = _make_context(notes_played=600)
        draft = run_job(context)

        # Should have strength about activity
        strengths = [f for f in draft["feedback"] if f["category"] == "strength"]
        note_feedback = [s for s in strengths if "notes_played" in str(s["evidence_refs"])]
        assert len(note_feedback) >= 1

    def test_always_has_encouragement(self):
        """Every summary includes encouragement."""
        context = _make_context(duration_seconds=60, notes_played=10)
        draft = run_job(context)

        encouragements = [f for f in draft["feedback"] if f["category"] == "encouragement"]
        assert len(encouragements) >= 1

    def test_summary_text_generated(self):
        """Summary text is generated."""
        context = _make_context()
        draft = run_job(context)

        assert "summary" in draft
        assert len(draft["summary"]) > 0

    def test_next_focus_generated(self):
        """Next focus area is suggested."""
        context = _make_context()
        draft = run_job(context)

        assert "next_focus" in draft
        assert "area" in draft["next_focus"]
        assert "reason" in draft["next_focus"]

    def test_session_score_computed(self):
        """Session score is computed."""
        context = _make_context()
        draft = run_job(context)

        assert "groove_score" in draft
        assert "overall" in draft["groove_score"]
        assert "trend" in draft["groove_score"]

    def test_streak_detection(self):
        """Session streaks are detected from history."""
        history = [
            {"completed": True, "duration_seconds": 600},
            {"completed": True, "duration_seconds": 700},
            {"completed": True, "duration_seconds": 650},
        ]
        context = _make_context(session_history=history)
        draft = run_job(context)

        # Should mention streak
        strengths = [f for f in draft["feedback"] if f["category"] == "strength"]
        streak_feedback = [s for s in strengths if "streak" in str(s["evidence_refs"])]
        assert len(streak_feedback) >= 1

    def test_rejects_wrong_kind(self):
        """Wrong kind is rejected."""
        context = _make_context()
        context["request"]["kind"] = "groove_feedback"

        with pytest.raises(ValueError, match="Unsupported request.kind"):
            run_job(context)

    def test_rejects_wrong_template(self):
        """Wrong template is rejected."""
        context = _make_context()
        context["request"]["template_id"] = "wrong_template"

        with pytest.raises(ValueError, match="Unsupported template"):
            run_job(context)


class TestPracticeSummarySimplified:
    """Test simplified entry point."""

    def test_run_practice_summary_basic(self):
        """Simplified entry point works."""
        context = {
            "session_id": "test-123",
            "session_stats": {
                "duration_seconds": 900,
                "notes_played": 300,
            },
        }
        draft = run_practice_summary(context)

        assert draft["session_id"] == "test-123"
        assert "feedback" in draft
        assert "groove_score" in draft
        assert "value" in draft["groove_score"]

    def test_run_practice_summary_with_history(self):
        """Simplified entry point handles history."""
        context = {
            "session_id": "test-456",
            "session_stats": {
                "duration_seconds": 1200,
                "notes_played": 400,
            },
            "session_history": [
                {"completed": True, "duration_seconds": 600},
                {"completed": True, "duration_seconds": 800},
            ],
        }
        draft = run_practice_summary(context)

        assert draft["session_id"] == "test-456"
        assert "feedback" in draft
