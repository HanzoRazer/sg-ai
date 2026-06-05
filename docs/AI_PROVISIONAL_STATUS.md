# AI Provisional Status

Sprint 41: Documentation of sg-ai's provisional output status.

## Overview

All outputs from sg-ai are **provisional** by default. This is a governance requirement, not a feature limitation.

## Key Rules

### 1. sg-ai Output is Provisional

Every generated artifact from sg-ai must include:

```python
{
    "provisional": True,
    "requires_approval": True,
    "generated_by": "sg-ai:GrooveLayerModel:<version>"
}
```

### 2. sg-ai Cannot Approve Its Own Output

The `approved_by` field can only be set by:
- Teacher review endpoints
- Explicit teacher override actions

sg-ai has no authority to:
- Set `provisional: false`
- Set `approved_by` to any value
- Bypass teacher approval

### 3. Teacher Approval Required for Canonization

Generated content transitions from provisional to canonical only when:

```python
{
    "provisional": False,
    "approved_by": "teacher_<id>",
    "approved_at": "2026-05-23T..."
}
```

This requires explicit teacher action through sg-agentd or sg-coach endpoints.

### 4. Deterministic sg-coach Does Not Depend on sg-ai

The coaching evaluation pipeline is deterministic:

```
sg-spec → sg-curriculum → sg-coach
```

sg-ai is NOT in this dependency chain. Deterministic coaching works without sg-ai.

sg-ai provides:
- Groove pattern generation
- Timing feedback enhancement
- Rhythm analysis

These are enhancements, not requirements.

## Integration Points

### sg-agentd

When `/regenerate` calls sg-ai generation:

```python
response = {
    "provisional": True,
    "requires_approval": True,
    "boundary_metadata": {
        "mutation_boundary": "regeneration_only",
        "provenance": "generated"
    }
}
```

### sg-coach

When coaching uses AI enhancement:

```python
enhancement = {
    "source": "sg-ai",
    "provisional": True,
    "confidence": 0.85,
    "requires_human_review": True
}
```

## Current Status

sg-ai is in active development but not required for core platform stability.

Sprint 41 requirements:
- [ ] Import smoke test passes (`import sg_engine`)
- [ ] This document exists
- [ ] Generated outputs marked provisional

Full test suite pass is NOT required for Sprint 41.

## Governance Verification

Run governance check:

```bash
cd sg-ai
python -c "import sg_engine; print('OK')"
```

Expected output: `OK`

## Related Documents

- [Repository Topology](../../sg-spec/docs/repository_topology.md)
- [Solo Practice Authority](../../sg-spec/docs/solo_practice_authority.md)
- [Provenance Enforcement](../../sg-spec/docs/provenance_enforcement.md)
