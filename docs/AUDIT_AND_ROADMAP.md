# sg-ai Audit & Development Roadmap

**Audit Date**: 2026-01-24
**Auditor**: Claude Code
**Version**: 1.0.0

---

## Part A: Architecture Audit

### 1. Current Structure

```
sg-ai/
├── packages/
│   └── sg-engine/
│       └── src/sg_engine/
│           ├── __init__.py          # Main entry: run_coaching_job()
│           ├── jobs/
│           │   ├── runner.py        # Job dispatch (JOB_REGISTRY)
│           │   └── groove_feedback.py # Only implemented job
│           ├── models/
│           │   └── registry.py      # GrooveLayerModel (rule-based v1)
│           ├── templates/
│           │   └── registry.py      # Template definitions
│           ├── governance.py        # PII blocking, evidence requirements
│           ├── session/
│           │   └── store.py         # In-memory session store
│           ├── api/
│           │   └── __init__.py      # REST endpoints
│           ├── device_runtime.py    # FastAPI + uvicorn server
│           ├── schemas/
│           │   ├── coach_context_packet_v1.json  # Input contract
│           │   └── coaching_draft_v1.json        # Output contract
│           └── fixtures/
│               └── vectors/         # Golden test vectors
└── tests/
    └── test_groove_feedback.py      # 14 tests passing
```

### 2. Component Inventory

#### Jobs (sg_engine/jobs/)

| Job ID | Status | Template | Description |
|--------|--------|----------|-------------|
| `groove_feedback` | **Implemented** | groove_feedback@1.0.0 | Analyzes timing/dynamics, produces coaching draft |
| `practice_summary` | **Registered only** | practice_summary@1.0.0 | Placeholder - raises NotImplementedError |

**Gap**: Only 1 of 2 registered jobs is implemented.

#### Models (sg_engine/models/)

| Model ID | Type | Status | Description |
|----------|------|--------|-------------|
| `GrooveLayerModel` | Rule-based | **Implemented** | Deterministic v1 coaching |
| (LLM model) | Neural | **Not implemented** | Future Mode-2 enhancement |

**Gap**: No LLM integration exists yet. All coaching is rule-based.

#### Templates (sg_engine/templates/)

| Template | Version | Status |
|----------|---------|--------|
| `groove_feedback` | 1.0.0 | **Active** |
| `practice_summary` | 1.0.0 | **Registered, no job** |

#### Governance (sg_engine/governance.py)

| Rule | Status | Description |
|------|--------|-------------|
| PII blocking | **Implemented** | Blocks names, emails, phone numbers |
| Evidence requirements | **Implemented** | Requires groove_metrics in context |
| No negative language | **Partial** | Template-based, not enforced at runtime |
| Confidence disclosure | **Implemented** | Required in coaching drafts |

#### API Endpoints (sg_engine/api/)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/sessions` | POST | **Implemented** - Create session |
| `/sessions/{id}` | GET | **Implemented** - Get session |
| `/sessions/{id}/context` | POST | **Implemented** - Add context |
| `/sessions/{id}/draft` | POST | **Implemented** - Generate draft |
| `/sessions/{id}/commit` | POST | **Implemented** - Commit draft |

#### Schemas (sg_engine/schemas/)

| Schema | Version | Status |
|--------|---------|--------|
| `coach_context_packet_v1.json` | 1.0.0 | **Defined** |
| `coaching_draft_v1.json` | 1.0.0 | **Defined** |

### 3. Integration Points

| Integration | Source Repo | Status |
|-------------|-------------|--------|
| `GrooveProfileV1` | sg-spec | **Available** (via sg_spec.schemas.groove_layer) |
| `GrooveControlIntentV1` | sg-spec | **Available** |
| `SessionRecord` | sg-spec | **Available** (via sg_spec.ai.coach.schemas) |
| `CoachEvaluation` | sg-spec | **Available** |
| `evaluate_session()` | sg-spec | **Available** (via sg_spec.ai.coach.coach_policy) |

### 4. Identified Gaps

| Gap ID | Category | Description | Priority |
|--------|----------|-------------|----------|
| G1 | Jobs | `practice_summary` job not implemented | High |
| G2 | Models | No LLM/neural model integration | Medium |
| G3 | Persistence | Session store is in-memory only | High |
| G4 | Testing | No integration tests with sg-coach | Medium |
| G5 | Governance | Runtime negative-language filter missing | Low |
| G6 | Schemas | No GrooveProfile→CoachContext adapter | Medium |
| G7 | Device | No offline queue/sync mechanism | Medium |
| G8 | Observability | No metrics/logging infrastructure | Low |

---

## Part B: Development Roadmap

### Phase 1: Foundation (Core Completeness)

**Goal**: Complete the core job registry and persistence layer.

| Task | Gap | Deliverable |
|------|-----|-------------|
| 1.1 Implement `practice_summary` job | G1 | `sg_engine/jobs/practice_summary.py` |
| 1.2 Add SQLite session persistence | G3 | `sg_engine/session/sqlite_store.py` |
| 1.3 GrooveProfile→CoachContext adapter | G6 | `sg_engine/adapters/groove_adapter.py` |
| 1.4 Integration tests with sg-coach | G4 | `tests/integration/test_coach_integration.py` |

**Exit Criteria**:
- All registered jobs have implementations
- Sessions persist across restarts
- sg-coach CoachEvaluation flows into sg-ai drafts

### Phase 2: Intelligence (Model Enhancement)

**Goal**: Add Mode-2 LLM capability while preserving Mode-1 fallback.

| Task | Gap | Deliverable |
|------|-----|-------------|
| 2.1 LLM model interface | G2 | `sg_engine/models/llm_interface.py` |
| 2.2 Ollama/local LLM adapter | G2 | `sg_engine/models/ollama_adapter.py` |
| 2.3 Model selection policy | G2 | `sg_engine/models/selector.py` |
| 2.4 Prompt templates | G2 | `sg_engine/prompts/` directory |

**Exit Criteria**:
- Local LLM can generate coaching text
- Mode-1 (rule-based) remains default
- Mode-2 activates only when LLM available and user opts in

### Phase 3: Device Runtime (Offline-First)

**Goal**: Enable true offline operation with eventual sync.

| Task | Gap | Deliverable |
|------|-----|-------------|
| 3.1 Offline draft queue | G7 | `sg_engine/sync/queue.py` |
| 3.2 Conflict resolution | G7 | `sg_engine/sync/resolver.py` |
| 3.3 Background sync service | G7 | `sg_engine/sync/service.py` |
| 3.4 Metrics collection | G8 | `sg_engine/observability/metrics.py` |

**Exit Criteria**:
- Device generates drafts without network
- Drafts sync when connectivity returns
- Basic telemetry for debugging

### Phase 4: Governance Hardening

**Goal**: Production-ready safety and compliance.

| Task | Gap | Deliverable |
|------|-----|-------------|
| 4.1 Runtime language filter | G5 | `sg_engine/governance/language_filter.py` |
| 4.2 Audit logging | G8 | `sg_engine/governance/audit.py` |
| 4.3 Rate limiting | - | `sg_engine/governance/rate_limit.py` |
| 4.4 Schema validation hardening | - | `sg_engine/governance/validators.py` |

**Exit Criteria**:
- All drafts pass language filter before output
- Full audit trail of coaching decisions
- Protected against abuse

---

## Dependency Graph

```
Phase 1 (Foundation)
    │
    ├──► Phase 2 (Intelligence) ──► Phase 4 (Governance)
    │                                    │
    └──► Phase 3 (Device Runtime) ◄──────┘
```

- Phase 2 and Phase 3 can proceed in parallel after Phase 1
- Phase 4 requires both Phase 2 and Phase 3

---

## Repository Boundary Compliance

Per `REPOSITORY_DECISION_MATRIX.md`:

| Artifact | Repo | Rationale |
|----------|------|-----------|
| `GrooveLayerModel` (rule engine) | sg-ai | Execution logic (HOW to phrase) |
| `GrooveProfileV1` (Pydantic) | sg-spec | Data shape (WHAT it looks like) |
| `evaluate_session()` (policy) | sg-spec | Coaching decision (WHAT to say) |
| `practice_summary` job | sg-ai | Draft generation (HOW to present) |
| SQLite store | sg-ai | Device persistence |
| LLM adapter | sg-ai | Local execution |

---

## Next Immediate Actions

1. **Create `practice_summary.py`** - Stub with same pattern as groove_feedback
2. **Add SQLite adapter** - Replace in-memory store
3. **Write integration test** - sg-coach → sg-ai pipeline

---

*This document should be updated as development progresses.*
