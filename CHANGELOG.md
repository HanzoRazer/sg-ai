# Changelog

All notable changes to sg-ai are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — Milestone: Explain + Drill Pack v1
- `explain_drill` job kind added to schemas
- `teaching_objectives[]` input field in `coach_context_packet_v1`
  - `objective_id`: stable identifier from sg-coach
  - `skill_area`: enum (tempo, dynamics, articulation, phrasing, rhythm, tone)
  - `description`: what the learner should achieve
  - `current_level`: 0-1 competency from sg-coach assessment
- `drill_packs[]` output field in `coaching_draft_v1`
  - `coaching_phrase`: 1-line explanation (max 120 chars)
  - `drill_steps`: exactly 2 concrete practice steps
  - `success_cue`: what success feels like (max 150 chars)
- `explain_drill` job handler in `jobs/explain_drill.py`
  - Rules-based content library for 6 skill areas
  - Deterministic output (same input = same output)
  - Template registered in `templates/registry.py`
  - Dispatch wired in `jobs/runner.py`
- Acceptance vector: `explain_drill_tempo_basics.json`
- Test suite: `tests/test_explain_drill.py` (13 tests)

### Boundary Decisions (sg-ai does NOT control)
- No timing decisions (when to show drill)
- No modality decisions (audio vs text vs haptic)
- No gating logic (unlocking prerequisites)
- sg-coach owns TeachingObjective lifecycle; sg-ai only explains + drills

### Added
- Initial repository scaffold
- `sg-engine` Python package with CLI (`sg-coach`)
- `coach_context_packet_v1` input schema
- `coaching_draft_v1` output schema
- `groove_feedback` job implementation
- Governance enforcement (no PII, evidence-cited feedback)
- CI workflows: `core_ci`, `vectors_gate`, `bundle_build`
- PR template with Groove Layer moat checklist
- Scripts: `build_bundle.py`, `run_vectors.py`, `check_goldens.py`, `new_vector.py`

### Groove Layer Behavior
- Rule-based feedback generation based on groove metrics
- Tempo stability analysis with threshold at 0.8
- Dynamics range analysis with threshold at 0.3/0.7
- Articulation clarity analysis with threshold at 0.75
- Next focus suggestion based on weakest metric
- Groove score computation (0-100 scale)

---

## Governance Notes

- **Vector changes require CHANGELOG update**: Any change to `fixtures/vectors/` must document the behavior change here.
- **Moat protection**: Changes to feedback generation logic require team review.
