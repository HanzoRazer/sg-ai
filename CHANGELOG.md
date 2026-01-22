# Changelog

All notable changes to sg-ai are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
