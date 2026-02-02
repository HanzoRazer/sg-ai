# tests/test_explain_drill.py
"""
Tests for explain_drill job (Explain + Drill Pack v1).
"""

import pytest
from sg_engine.jobs.explain_drill import run_job, _select_content, _generate_drill_packs


def _make_context(
    teaching_objectives: list = None,
    tempo_bpm: int = 80,
):
    """Build a valid explain_drill context (schema-perfect)."""
    return {
        "schema_id": "coach_context_packet_v1",
        "schema_version": "v1",
        "created_at_utc": "2026-02-01T12:00:00Z",
        "session_id": "test-001",
        "request": {
            "kind": "explain_drill",
            "template_id": "explain_drill",
            "template_version": "1.0.0",
            "teaching_objectives": teaching_objectives or [],
        },
        "evidence": {
            "groove_metrics": {},
            "session_stats": {"tempo_bpm": tempo_bpm},
        },
    }


class TestExplainDrillJob:
    """Test suite for explain_drill job."""

    def test_schema_perfect_minimal(self):
        """Schema-perfect context produces schema-perfect output."""
        context = {
            "schema_id": "coach_context_packet_v1",
            "schema_version": "v1",
            "created_at_utc": "2026-02-01T12:00:00Z",
            "session_id": "test-001",
            "request": {
                "kind": "explain_drill",
                "template_id": "explain_drill",
                "template_version": "1.0.0",
                "teaching_objectives": [
                    {
                        "objective_id": "tempo_steady_quarter",
                        "skill_area": "tempo",
                        "description": "Maintain steady quarter note pulse at 80 BPM",
                        "current_level": 0.45,
                    }
                ],
            },
            "evidence": {
                "groove_metrics": {},
                "session_stats": {},
            },
        }

        draft = run_job(context)

        # Top-level required fields
        assert draft["schema_id"] == "coaching_draft_v1"
        assert draft["schema_version"] == "v1"
        assert draft["kind"] == "explain_drill"

        # model required fields
        assert draft["model"]["id"] == "groove_layer_v1"
        assert draft["model"]["runtime"] == "local"

        # template required fields
        assert draft["template"]["id"] == "explain_drill"
        assert draft["template"]["version"] == "1.0.0"

        # feedback required (at least 1 item)
        assert isinstance(draft["feedback"], list)
        assert len(draft["feedback"]) >= 1
        for fb in draft["feedback"]:
            assert "category" in fb
            assert "text" in fb
            assert "evidence_refs" in fb

        # drill_packs
        assert isinstance(draft["drill_packs"], list)
        assert len(draft["drill_packs"]) == 1
        pack = draft["drill_packs"][0]

        # drill_pack item required fields
        assert pack["objective_id"] == "tempo_steady_quarter"
        assert isinstance(pack["coaching_phrase"], str)
        assert 1 <= len(pack["coaching_phrase"]) <= 120
        assert isinstance(pack["drill_steps"], list)
        assert len(pack["drill_steps"]) == 2
        assert all(isinstance(s, str) and len(s) > 0 for s in pack["drill_steps"])
        assert isinstance(pack["success_cue"], str)
        assert 1 <= len(pack["success_cue"]) <= 150

    def test_returns_correct_structure(self):
        """Job returns a valid CoachingDraft with drill_packs."""
        context = _make_context(
            teaching_objectives=[
                {
                    "objective_id": "tempo_test",
                    "skill_area": "tempo",
                    "description": "Test tempo objective",
                    "current_level": 0.5,
                }
            ]
        )
        draft = run_job(context)

        assert draft["schema_id"] == "coaching_draft_v1"
        assert draft["kind"] == "explain_drill"
        assert "feedback" in draft
        assert "drill_packs" in draft
        assert len(draft["drill_packs"]) == 1

    def test_drill_pack_has_required_fields(self):
        """Each drill pack has objective_id, coaching_phrase, drill_steps, success_cue."""
        context = _make_context(
            teaching_objectives=[
                {
                    "objective_id": "dynamics_test",
                    "skill_area": "dynamics",
                    "description": "Test dynamics",
                    "current_level": 0.3,
                }
            ]
        )
        draft = run_job(context)
        dp = draft["drill_packs"][0]

        assert dp["objective_id"] == "dynamics_test"
        assert isinstance(dp["coaching_phrase"], str)
        assert len(dp["coaching_phrase"]) <= 120
        assert isinstance(dp["drill_steps"], list)
        assert len(dp["drill_steps"]) == 2
        assert isinstance(dp["success_cue"], str)
        assert len(dp["success_cue"]) <= 150

    def test_multiple_objectives_produce_multiple_packs(self):
        """Each teaching objective gets its own drill pack."""
        context = _make_context(
            teaching_objectives=[
                {"objective_id": "obj1", "skill_area": "tempo", "description": "Obj 1"},
                {"objective_id": "obj2", "skill_area": "dynamics", "description": "Obj 2"},
                {"objective_id": "obj3", "skill_area": "articulation", "description": "Obj 3"},
            ]
        )
        draft = run_job(context)

        assert len(draft["drill_packs"]) == 3
        ids = [dp["objective_id"] for dp in draft["drill_packs"]]
        assert ids == ["obj1", "obj2", "obj3"]

    def test_empty_objectives_raises_error(self):
        """Empty objectives raises ValueError (explain_drill requires objectives)."""
        context = _make_context(teaching_objectives=[])

        with pytest.raises(ValueError, match="explain_drill requires request.teaching_objectives"):
            run_job(context)

    def test_missing_objectives_raises_error(self):
        """Missing objectives raises ValueError."""
        context = {
            "schema_id": "coach_context_packet_v1",
            "schema_version": "v1",
            "created_at_utc": "2026-02-01T12:00:00Z",
            "session_id": "test-001",
            "request": {
                "kind": "explain_drill",
                "template_id": "explain_drill",
                "template_version": "1.0.0",
                # teaching_objectives omitted
            },
            "evidence": {"groove_metrics": {}, "session_stats": {}},
        }

        with pytest.raises(ValueError, match="explain_drill requires request.teaching_objectives"):
            run_job(context)

    def test_tempo_bpm_substituted_in_drills(self):
        """Drill steps with BPM placeholders get actual values substituted."""
        # Use an objective_id that selects a drill template with BPM placeholders
        context = _make_context(
            teaching_objectives=[
                {"objective_id": "a", "skill_area": "tempo", "description": "Test", "current_level": 0.5}
            ],
            tempo_bpm=120,
        )
        draft = run_job(context)
        dp = draft["drill_packs"][0]

        # Verify no unsubstituted placeholders remain
        all_text = " ".join(dp["drill_steps"])
        assert "{bpm}" not in all_text
        assert "{half_bpm}" not in all_text

    def test_deterministic_output(self):
        """Same input always produces same output."""
        context = _make_context(
            teaching_objectives=[
                {"objective_id": "determinism_test", "skill_area": "phrasing", "description": "Test", "current_level": 0.5}
            ]
        )

        draft1 = run_job(context)
        draft2 = run_job(context)

        assert draft1["drill_packs"] == draft2["drill_packs"]

    def test_all_skill_areas_supported(self):
        """All skill_area enum values produce valid output."""
        skill_areas = ["tempo", "dynamics", "articulation", "phrasing", "rhythm", "tone"]

        for skill in skill_areas:
            context = _make_context(
                teaching_objectives=[
                    {"objective_id": f"{skill}_test", "skill_area": skill, "description": f"Test {skill}", "current_level": 0.5}
                ]
            )
            draft = run_job(context)

            assert len(draft["drill_packs"]) == 1
            dp = draft["drill_packs"][0]
            assert len(dp["coaching_phrase"]) > 0
            assert len(dp["drill_steps"]) == 2
            assert len(dp["success_cue"]) > 0


class TestSelectContent:
    """Tests for content selection logic."""

    def test_unknown_skill_falls_back_to_tempo(self):
        """Unknown skill_area uses tempo content as fallback."""
        content = _select_content("unknown_skill", "test_id", 0.5)
        
        assert "coaching_phrase" in content
        assert "drill_steps" in content
        assert "success_cue" in content

    def test_same_objective_id_same_content(self):
        """Deterministic: same objective_id always selects same content."""
        c1 = _select_content("tempo", "my_objective", 0.5)
        c2 = _select_content("tempo", "my_objective", 0.5)

        assert c1 == c2

    def test_different_objective_id_may_differ(self):
        """Different objective_ids may select different content."""
        c1 = _select_content("tempo", "objective_a", 0.5)
        c2 = _select_content("tempo", "objective_b", 0.5)

        # They might be same or different depending on hash
        # Just verify both are valid
        assert len(c1["drill_steps"]) == 2
        assert len(c2["drill_steps"]) == 2


class TestGovernanceCompliance:
    """Tests for governance rule compliance."""

    def test_feedback_has_evidence_refs(self):
        """All feedback items have evidence_refs (governance requirement)."""
        context = _make_context(
            teaching_objectives=[
                {"objective_id": "gov_test", "skill_area": "tempo", "description": "Test"}
            ]
        )
        draft = run_job(context)

        for fb in draft["feedback"]:
            assert "evidence_refs" in fb
            assert len(fb["evidence_refs"]) >= 1

    def test_model_runtime_is_local(self):
        """Model runtime must be 'local' (offline device)."""
        context = _make_context(
            teaching_objectives=[
                {"objective_id": "runtime_test", "skill_area": "tempo", "description": "Test"}
            ]
        )
        draft = run_job(context)

        assert draft["model"]["runtime"] == "local"

    def test_no_timing_modality_gating_fields(self):
        """Output must not contain timing, modality, or gating fields."""
        context = _make_context(
            teaching_objectives=[
                {"objective_id": "boundary_test", "skill_area": "tempo", "description": "Test"}
            ]
        )
        draft = run_job(context)

        # These fields should NOT exist (sg-coach owns them)
        forbidden_fields = ["show_at", "modality", "gate", "prerequisite", "unlock", "schedule"]
        
        for field in forbidden_fields:
            assert field not in draft
            for dp in draft["drill_packs"]:
                assert field not in dp
