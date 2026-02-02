# SG-AI Copilot Instructions

## Project Overview

`sg-ai` is an **offline AI coach** (Groove Layer) for Smart Guitar devices. It operates as a pure function:
- **Input**: `CoachContextPacket` (JSON validated against `coach_context_packet_v1.json`)
- **Output**: `CoachingDraft` (JSON validated against `coaching_draft_v1.json`)
- **No side effects, no external API calls, no PII storage**

## Current Milestone: Explain + Drill Pack v1

For each `TeachingObjective` (from sg-coach), sg-ai provides:
- **coaching_phrase**: 1-line explanation (max 120 chars)
- **drill_steps**: exactly 2 concrete practice steps
- **success_cue**: what success feels like (sensory cue)

**Boundary**: sg-ai does NOT decide timing, modality, or gating. sg-coach owns the teaching plan.

## Architecture

```
packages/sg-engine/src/sg_engine/
├── jobs/                 # Job handlers (groove_feedback, practice_summary)
├── schemas/              # JSON schemas (bundled, not network-loaded)
├── templates/registry.py # Versioned template specs
├── governance.py         # PII/content field blocking
├── device_runtime.py     # FastAPI server for device
└── api/__init__.py       # REST endpoints (/api/session/*)
```

**Data Flow**: Device → `CoachContextPacket` → `run_coaching_job()` → `CoachingDraft` → Device

## Critical Developer Commands

```bash
cd packages/sg-engine

# Install & run (uses uv, not pip)
uv sync --all-extras
uv run pytest                    # Run tests
uv run ruff check src/           # Lint
uv run ruff format src/          # Format
uv run pyright src/sg_engine/    # Type check

# CLI usage
uv run sg-coach run-job --in context.json --out draft.json
uv run sg-coach validate --context context.json

# Run acceptance vectors (from repo root)
python scripts/run_vectors.py --strict
```

## Governance Rules (Non-Negotiable)

1. **No PII fields** — Never add: `player_id`, `account_id`, `email`, `user_id`, etc. See `FORBIDDEN_PII_FIELDS` in [governance.py](packages/sg-engine/src/sg_engine/governance.py)
2. **No raw content** — Never reference: `audio_url`, `recording_path`, `video_url`
3. **Evidence-cited feedback** — Every `feedback[]` item MUST have `evidence_refs[]` array
4. **No judgmental language** — Avoid: "terrible", "awful", "failed" (see `ensure_no_scoring_language()`)

## Adding New Jobs

1. Create handler in `packages/sg-engine/src/sg_engine/jobs/` (follow `groove_feedback.py` pattern)
2. Register template in `templates/registry.py`
3. Add dispatch case in `jobs/runner.py`
4. Add acceptance vector in `fixtures/vectors/`
5. **Update CHANGELOG.md** when vectors change

## Vector-Locked Behavior (Moat Protection)

Changes to Groove Layer feedback logic are protected by acceptance vectors:
- Vectors live in `fixtures/vectors/*.json`
- CI runs `scripts/run_vectors.py --strict`
- **Any vector change requires CHANGELOG.md update and team review**

Example vector structure:
```json
{
  "_meta": { "name": "sample_high_tempo_stability", "category": "core" },
  "input": { "schema_id": "coach_context_packet_v1", ... },
  "expected": { "kind": "groove_feedback", "expect_strength_in": ["tempo_stability"] }
}
```

## sg-spec Integration

Types from `sg-spec` are re-exported in [coach_types.py](packages/sg-engine/src/sg_engine/coach_types.py):
```python
from sg_engine.coach_types import CoachFinding, Severity, CoachEvaluation
```

Schemas are vendored in `contracts/` — update via sg-spec first, then vendor here.

## Exit Codes (CLI)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Schema validation error |
| 2 | Governance violation (PII detected) |
| 3 | Model runtime error |
| 4 | Unsupported job/template |

## Bundle Building

```bash
python scripts/build_bundle.py --version 1.0.0
python scripts/build_bundle.py --version 1.0.0 --include-ui  # With sg-app
```

Output: Deterministic ZIP with manifest, Python source, and optional UI.
