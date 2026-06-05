# tests/test_sg_spec_integration.py
"""
Integration tests for sg-spec coach schema types.

Verifies that:
1. sg_spec.schemas.coach_schemas can be imported
2. coach_types.py re-exports work correctly
3. to_coach_finding() conversion produces valid CoachFinding
"""
import pytest


class TestSgSpecImports:
    """Test that sg-spec types can be imported."""

    def test_import_from_sg_spec_directly(self):
        """Import types directly from sg-spec."""
        from sg_spec.schemas.coach_schemas import (
            CoachFinding,
            CoachEvaluation,
            Severity,
            FindingEvidence,
            SessionRecord,
        )

        # Verify types are accessible
        assert CoachFinding is not None
        assert CoachEvaluation is not None
        assert Severity.primary == "primary"

    def test_import_via_coach_types(self):
        """Import types via sg_engine.coach_types re-export."""
        from sg_engine.coach_types import (
            CoachFinding,
            Severity,
            FindingEvidence,
            CoachEvaluation,
        )

        # Verify types are accessible
        assert CoachFinding is not None
        assert Severity.info == "info"


class TestToCoachFindingConversion:
    """Test groove feedback to CoachFinding conversion."""

    def test_convert_strength_feedback(self):
        """Convert a 'strength' feedback item."""
        from sg_engine.jobs.groove_feedback import to_coach_finding
        from sg_engine.coach_types import Severity

        feedback_item = {
            "category": "strength",
            "text": "Your tempo consistency is excellent!",
            "evidence_refs": [{"metric": "tempo_stability", "value": 0.85}],
            "priority": 2,
        }

        finding = to_coach_finding(feedback_item)

        assert finding.type == "technique"
        assert finding.severity == Severity.info
        assert "tempo consistency" in finding.interpretation
        assert finding.evidence.metric == "tempo_stability"
        assert finding.evidence.value == 0.85

    def test_convert_focus_area_feedback(self):
        """Convert a 'focus_area' feedback item."""
        from sg_engine.jobs.groove_feedback import to_coach_finding
        from sg_engine.coach_types import Severity

        feedback_item = {
            "category": "focus_area",
            "text": "Let's work on tempo consistency.",
            "evidence_refs": [{"metric": "tempo_stability", "value": 0.35}],
            "priority": 1,
        }

        finding = to_coach_finding(feedback_item)

        assert finding.type == "timing"
        assert finding.severity == Severity.primary
        assert finding.evidence.value == 0.35

    def test_convert_tip_feedback(self):
        """Convert a 'tip' feedback item."""
        from sg_engine.jobs.groove_feedback import to_coach_finding
        from sg_engine.coach_types import Severity

        feedback_item = {
            "category": "tip",
            "text": "Try adding more dynamic contrast.",
            "evidence_refs": [{"metric": "dynamics_range", "value": 0.25}],
            "priority": 2,
        }

        finding = to_coach_finding(feedback_item)

        assert finding.type == "technique"
        assert finding.severity == Severity.secondary

    def test_convert_encouragement_feedback(self):
        """Convert an 'encouragement' feedback item."""
        from sg_engine.jobs.groove_feedback import to_coach_finding
        from sg_engine.coach_types import Severity

        feedback_item = {
            "category": "encouragement",
            "text": "Keep up the great work!",
            "evidence_refs": [{"metric": "tempo_stability", "value": 0.7}],
            "priority": 5,
        }

        finding = to_coach_finding(feedback_item)

        assert finding.type == "other"
        assert finding.severity == Severity.info

    def test_finding_is_valid_pydantic_model(self):
        """Verify the finding can be serialized/validated."""
        from sg_engine.jobs.groove_feedback import to_coach_finding

        feedback_item = {
            "category": "strength",
            "text": "Great timing!",
            "evidence_refs": [{"metric": "beat_accuracy", "value": 0.9}],
            "priority": 2,
        }

        finding = to_coach_finding(feedback_item)

        # Should be able to convert to dict and back
        data = finding.model_dump()
        assert "type" in data
        assert "severity" in data
        assert "evidence" in data
        assert "interpretation" in data

    def test_long_text_truncated(self):
        """Verify long text is truncated to 240 chars."""
        from sg_engine.jobs.groove_feedback import to_coach_finding

        long_text = "A" * 300  # 300 characters

        feedback_item = {
            "category": "tip",
            "text": long_text,
            "evidence_refs": [],
            "priority": 3,
        }

        finding = to_coach_finding(feedback_item)

        assert len(finding.interpretation) == 240


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_groove_feedback_to_findings_batch(self):
        """Run groove analysis and convert all findings."""
        from sg_engine.jobs.groove_feedback import _analyze_metrics, to_coach_finding
        from sg_engine.coach_types import CoachFinding

        evidence = {
            "groove_metrics": {
                "tempo_stability": 0.85,
                "dynamics_range": 0.25,
                "articulation_clarity": 0.9,
            }
        }

        feedback_items = _analyze_metrics(evidence)
        findings = [to_coach_finding(item) for item in feedback_items]

        # Should have multiple findings
        assert len(findings) >= 2

        # All should be valid CoachFinding instances
        for f in findings:
            assert isinstance(f, CoachFinding)
            assert f.interpretation  # not empty
