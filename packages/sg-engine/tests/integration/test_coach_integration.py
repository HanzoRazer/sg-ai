# tests/integration/test_coach_integration.py
"""
Integration tests: sg-ai with sg-coach and sg-spec.

These tests verify the complete pipeline:
1. sg-spec: Data models (SessionRecord, CoachEvaluation, GrooveProfileV1)
2. sg-coach: Coaching policy (evaluate_session)
3. sg-ai: Feedback generation (run_groove_feedback, run_practice_summary)

Requirements:
- sg-spec must be installed
- Tests use real sg-spec models (no mocks)
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

# Skip all tests if sg-spec is not installed
pytest.importorskip("sg_spec")

from sg_spec.ai.coach.schemas import (
    SessionRecord,
    PerformanceSummary,
    TimingErrorStats,
    SessionTiming,
    SessionEvents,
    ProgramRef,
    ProgramType,
    ClaveKind,
)
from sg_spec.ai.coach.coach_policy import evaluate_session
from sg_spec.schemas.groove_layer import (
    GrooveProfileV1,
    TimingBias,
    TempoStability,
    SubdivisionFidelity,
    ErrorRecovery,
    GrooveElasticity,
    ConfidenceBand,
    EvidenceWindow,
)

from sg_engine.jobs.groove_feedback import run_groove_feedback, to_coach_finding
from sg_engine.jobs.practice_summary import run_practice_summary
from sg_engine.adapters.groove_adapter import (
    groove_profile_to_metrics,
    session_record_to_stats,
    coach_evaluation_to_context,
    build_groove_feedback_context,
    build_practice_summary_context,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def session_record():
    """Create a real SessionRecord from sg-spec."""
    return SessionRecord(
        session_id=uuid4(),
        instrument_id="sg-test-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="salsa_minor_dm",
            hash="sha256:" + "a" * 64,
        ),
        timing=SessionTiming(
            bpm=110,
            grid=16,
            clave=ClaveKind.son_2_3,
            strict=True,
            late_drop_ms=35,
        ),
        duration_s=600,
        performance=PerformanceSummary(
            bars_played=64,
            notes_expected=512,
            notes_played=480,
            notes_dropped=32,
            timing_error_ms=TimingErrorStats(mean=18.4, std=9.2, max=41.7),
            error_by_step={"0": 4.1, "3": 22.5, "7": 38.8, "11": 19.4},
        ),
        events=SessionEvents(late_drops=7, panic_triggered=False),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def groove_profile():
    """Create a real GrooveProfileV1 from sg-spec."""
    now = datetime.now(timezone.utc).isoformat()
    return GrooveProfileV1(
        profile_id="test-profile-001",
        scope="device_local",
        timing_bias=TimingBias(
            mean_offset_ms=5.0,
            stddev_ms=3.0,
            direction="ahead",
            confidence=0.85,
        ),
        tempo_stability=TempoStability(
            supported_bpm_range=(80, 140),
            drift_slope=0.01,
            fatigue_sensitivity=0.3,
            confidence=0.9,
        ),
        subdivision_fidelity=SubdivisionFidelity(
            supported=["quarter", "eighth", "sixteenth"],
            unstable=["triplet_eighth"],
            swing_tolerance=0.7,
            confidence=0.88,
        ),
        error_recovery=ErrorRecovery(
            mean_recovery_beats=2.5,
            panic_probability=0.1,
            self_correction_rate=0.8,
        ),
        groove_elasticity=GrooveElasticity(
            microtiming_flex_ms=15.0,
            lock_threshold=0.75,
            push_pull_balance="balanced",
        ),
        confidence_band=ConfidenceBand(lower=0.7, upper=0.95),
        evidence_window=EvidenceWindow(sessions=10, events=5000),
        created_at_utc=now,
        updated_at_utc=now,
    )


# =============================================================================
# Integration Tests
# =============================================================================

class TestSgCoachToSgAiPipeline:
    """Test the sg-coach → sg-ai pipeline."""

    def test_session_to_evaluation_to_feedback(self, session_record):
        """SessionRecord → CoachEvaluation → groove_feedback draft."""
        # Step 1: sg-spec/sg-coach evaluates the session
        evaluation = evaluate_session(session_record)

        # Verify evaluation
        assert evaluation.session_id == session_record.session_id
        assert len(evaluation.findings) >= 1  # Should have timing finding
        assert evaluation.confidence > 0

        # Step 2: Convert to sg-ai context
        stats = session_record_to_stats(session_record)
        coach_ctx = coach_evaluation_to_context(evaluation)

        # Step 3: Run sg-ai groove_feedback
        context = {
            "session_id": str(session_record.session_id),
            "groove_metrics": {
                "tempo_stability": 0.7,
                "dynamics_range": 0.65,
                "articulation_clarity": 0.75,
            },
            "session_stats": stats,
        }
        draft = run_groove_feedback(context)

        # Verify draft
        assert draft["kind"] == "groove_feedback"
        assert len(draft["feedback"]) >= 1
        assert "groove_score" in draft

    def test_profile_adapter_produces_valid_metrics(self, groove_profile):
        """GrooveProfileV1 → groove_metrics for job context."""
        metrics = groove_profile_to_metrics(groove_profile)

        # Verify all required metrics
        assert "tempo_stability" in metrics
        assert "beat_accuracy" in metrics
        assert "dynamics_range" in metrics
        assert "articulation_clarity" in metrics
        assert "phrase_coherence" in metrics

        # Verify values are in expected range
        assert 0 <= metrics["tempo_stability"] <= 1
        assert 0 <= metrics["beat_accuracy"] <= 1
        assert 0 <= metrics["dynamics_range"] <= 1

    def test_session_adapter_produces_valid_stats(self, session_record):
        """SessionRecord → session_stats for job context."""
        stats = session_record_to_stats(session_record)

        # Verify all required fields
        assert stats["duration_seconds"] == 600
        assert stats["notes_played"] == 480
        assert stats["notes_dropped"] == 32
        assert stats["bpm"] == 110
        assert stats["program_name"] == "salsa_minor_dm"

    def test_build_context_produces_runnable_input(self, groove_profile, session_record):
        """build_groove_feedback_context produces context that runs."""
        context = build_groove_feedback_context(groove_profile, session_record)

        # Run the job
        draft = run_groove_feedback(context)

        # Verify it worked
        assert draft["kind"] == "groove_feedback"
        assert "feedback" in draft


class TestSgAiFindingToSgSpec:
    """Test sg-ai → sg-spec conversion (reverse direction)."""

    def test_feedback_item_to_coach_finding(self):
        """sg-ai feedback item converts to sg-spec CoachFinding."""
        # Generate feedback
        context = {
            "session_id": "test-123",
            "groove_metrics": {"tempo_stability": 0.4},  # Low stability
            "session_stats": {"duration_seconds": 600, "notes_played": 100},
        }
        draft = run_groove_feedback(context)

        # Convert feedback items to CoachFinding
        for item in draft["feedback"]:
            finding = to_coach_finding(item)

            # Verify it's a valid CoachFinding
            assert hasattr(finding, "type")
            assert hasattr(finding, "severity")
            assert hasattr(finding, "interpretation")
            assert len(finding.interpretation) <= 240  # Schema limit


class TestPracticeSummaryIntegration:
    """Test practice_summary with sg-spec models."""

    def test_session_to_summary(self, session_record):
        """SessionRecord → practice_summary draft."""
        context = build_practice_summary_context(session_record)
        draft = run_practice_summary(context)

        assert draft["kind"] == "practice_summary"
        assert "summary" in draft
        assert "feedback" in draft
        assert len(draft["feedback"]) >= 1

    def test_session_with_evaluation_to_summary(self, session_record):
        """SessionRecord + CoachEvaluation → richer summary."""
        evaluation = evaluate_session(session_record)
        context = build_practice_summary_context(
            session_record,
            evaluation=evaluation,
        )

        # Coach context should be included
        assert "coach_context" in context
        assert "coach_findings" in context["coach_context"]

        # Run summary
        draft = run_practice_summary(context)
        assert draft["kind"] == "practice_summary"


class TestRoundTrip:
    """Test full round-trip through the system."""

    def test_complete_coaching_cycle(self, session_record, groove_profile):
        """
        Complete cycle:
        1. SessionRecord (player action)
        2. CoachEvaluation (sg-coach analysis)
        3. groove_feedback draft (sg-ai generation)
        4. CoachFinding[] (back to sg-spec format)
        """
        # 1. Start with session record
        session = session_record

        # 2. Evaluate with sg-coach
        evaluation = evaluate_session(session)
        assert evaluation.confidence > 0

        # 3. Generate feedback with sg-ai
        context = build_groove_feedback_context(groove_profile, session)
        draft = run_groove_feedback(context)
        assert len(draft["feedback"]) >= 1

        # 4. Convert back to sg-spec format
        findings = [to_coach_finding(item) for item in draft["feedback"]]
        assert len(findings) >= 1

        # Verify findings are valid sg-spec objects
        for finding in findings:
            # Can serialize to dict (Pydantic model)
            finding_dict = finding.model_dump()
            assert "type" in finding_dict
            assert "severity" in finding_dict
