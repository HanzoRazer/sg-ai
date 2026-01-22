# sg-ai

**Offline AI Coach for Smart Guitar — Groove Layer Intelligence**

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)]()

## Overview

`sg-ai` is an **offline AI coach** that powers the Groove Layer on Smart Guitar devices. It operates as a pure function:

- **Input**: `CoachContextPacket` (JSON, schema-validated)
- **Output**: `CoachingDraft` (JSON, schema-validated)
- **Side effects**: None

### Key Principles

1. **Offline device worker** — runs entirely on-device, no external API calls
2. **Schema in, schema out** — strict JSON schema validation at both ends
3. **Privacy-first** — no PII storage, no user data leaks
4. **Real-time capable** — latency budget enforced via CI
5. **Groove Layer moat** — behavior locked via acceptance vectors

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Practice Session│────▶│     sg-ai        │────▶│  CoachingDraft  │
│ (device context)│     │  (Groove Layer)  │     │  (feedback)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/HanzoRazer/sg-ai.git
cd sg-ai

# Install Python package
cd packages/sg-engine
pip install -e .

# Or build device bundle
python scripts/build_bundle.py
```

## Usage

### CLI Mode

```bash
# Run a coaching job
sg-coach run-job --in context.json --out draft.json

# Validate schemas only
sg-coach validate --context context.json
sg-coach validate --draft draft.json
```

**Exit Codes:**
- `0` — Success
- `1` — Validation error
- `2` — Governance violation (PII detected)
- `3` — Model runtime error

### Python API

```python
from sg_engine import run_coaching_job
from sg_engine.schemas import CoachContextPacket

context = CoachContextPacket(
    schema_id="coach_context_packet_v1",
    session_id="practice-2026-01-21",
    # ...
)

draft = run_coaching_job(context)
```

## Supported Job Types

### Wave 1 (v1)

| Kind | Template | Status |
|------|----------|--------|
| `groove_feedback` | `groove_feedback@v1` | ✅ Active |
| `practice_summary` | `practice_summary@v1` | ✅ Active |

### Future

| Kind | Template | Status |
|------|----------|--------|
| `technique_hint` | `technique_hint@v1` | 🔜 Wave 2 |
| `repertoire_suggest` | `repertoire_suggest@v1` | 🔜 Wave 2 |

## Governance

This repository enforces hard governance rules:

1. **No PII storage** — No player_id, account_id, emails in schemas/logs
2. **No raw user content** — No audio blobs, recordings in repo
3. **Latency budget** — Real-time constraints enforced via CI
4. **Vector-locked behavior** — Groove Layer changes require golden updates

## Repository Structure

```
sg-ai/
├── packages/
│   ├── sg-engine/          # Python Groove Layer + policy
│   └── sg-app/             # TypeScript UI (if applicable)
├── contracts/              # SG-only schemas
├── fixtures/vectors/       # Acceptance vectors + goldens
├── scripts/                # Developer tools
├── docs/adr/               # Architecture Decision Records
└── .github/                # CI workflows + templates
```

## Documentation

- [Contracts](contracts/README.md) — Schema definitions
- [ADR Index](docs/adr/README.md) — Architecture decisions
- [Contributing](CONTRIBUTING.md) — Development guide

## License

Proprietary - All rights reserved.
