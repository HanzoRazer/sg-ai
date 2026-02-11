# SG-AI Copilot Instructions

## What This Is
Offline AI coach (Groove Layer) for Smart Guitar. Pure function: `CoachContextPacket` → `run_coaching_job()` → `CoachingDraft`. No external APIs, no PII.

## Developer Commands
```bash
cd packages/sg-engine
uv sync --all-extras              # Install (uses uv, NOT pip)
uv run pytest                     # Tests
uv run ruff check src/ && uv run ruff format src/  # Lint+format
uv run pyright src/sg_engine/     # Type check
python scripts/run_vectors.py --strict  # Acceptance vectors (from repo root)
```

## Architecture & Data Flow
```
Device → CoachContextPacket → jobs/runner.py → [job handler] → CoachingDraft → Device
```

Key paths in `packages/sg-engine/src/sg_engine/`:
- **jobs/runner.py** — Dispatch by `request.kind` + `template_id`
- **jobs/*.py** — Job handlers (groove_feedback, explain_drill, practice_summary)
- **governance.py** — PII blocking, evidence enforcement
- **schemas/** — Bundled JSON schemas (no network loading)
- **coach_types.py** — Re-exports from `sg-spec` (CoachFinding, Severity, etc.)

## Hard Governance Rules
1. **No PII fields** — See `FORBIDDEN_PII_FIELDS` in [governance.py](packages/sg-engine/src/sg_engine/governance.py): `player_id`, `account_id`, `email`, `user_id`, etc.
2. **No raw content refs** — Never use: `audio_url`, `recording_path`, `video_url`
3. **Evidence required** — Every `feedback[]` item needs `evidence_refs[]` array
4. **No judgmental language** — Forbidden words: `terrible`, `awful`, `horrible`, `failed`, `failure`, `wrong`
5. Violations raise `GovernanceViolation` (exit code 2)

## Adding a New Job
1. Create `jobs/{job_name}.py` — follow [groove_feedback.py](packages/sg-engine/src/sg_engine/jobs/groove_feedback.py) pattern
2. Add dispatch in [runner.py](packages/sg-engine/src/sg_engine/jobs/runner.py):
   ```python
   if kind == "my_job" and template_id == "my_job":
       return run_my_job(context)
   ```
3. Register template in [templates/registry.py](packages/sg-engine/src/sg_engine/templates/registry.py)
4. Add acceptance vector in `fixtures/vectors/` + update `CHANGELOG.md`

## Vector-Locked Behavior
Groove Layer logic is protected by acceptance vectors:
- Vectors: `fixtures/vectors/*.json` — define input/expected output pairs
- CI gate: `scripts/run_vectors.py --strict`
- **Any vector change requires CHANGELOG.md update**

Vector structure:
```json
{
  "_meta": { "name": "sample_high_tempo_stability", "category": "core" },
  "input": { "schema_id": "coach_context_packet_v1", "request": { "kind": "groove_feedback", "template_id": "groove_feedback" }, ... },
  "expected": { "kind": "groove_feedback", "expect_strength_in": ["tempo_stability"] }
}
```

## Current Milestone: Explain + Drill Pack v1
For `explain_drill` jobs, output `drill_packs[]` with:
- `coaching_phrase`: max 120 chars
- `drill_steps`: exactly 2 steps
- `success_cue`: max 150 chars

**Boundary**: sg-ai does NOT decide timing/modality/gating — sg-coach owns the teaching plan.

## sg-spec Integration
Types re-exported from `sg-spec` in [coach_types.py](packages/sg-engine/src/sg_engine/coach_types.py):
```python
from sg_engine.coach_types import CoachFinding, Severity, CoachEvaluation
```

## CLI Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Schema validation error |
| 2 | Governance violation (PII) |
| 3 | Model runtime error |
| 4 | Unsupported job/template |

## Device Runtime (FastAPI)
On-device server in [device_runtime.py](packages/sg-engine/src/sg_engine/device_runtime.py):
```bash
uv run uvicorn sg_engine.device_runtime:create_app --factory
```

API endpoints (see [api/__init__.py](packages/sg-engine/src/sg_engine/api/__init__.py)):
- `GET /api/status` — health + versions
- `POST /api/session/start` — start coaching session
- `POST /api/session/event` — ingest groove events
- `GET /api/session/state` — current session state
- `POST /api/session/stop` — end session

## Bundle Building
```bash
python scripts/build_bundle.py --version 1.0.0
python scripts/build_bundle.py --version 1.0.0 --include-ui  # With sg-app
```

Output: Deterministic ZIP with manifest, Python source, contracts, and optional UI (`sg-app/dist`).
