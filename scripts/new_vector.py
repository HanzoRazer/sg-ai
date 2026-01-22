#!/usr/bin/env python3
"""
Create a new acceptance vector with fixture and test stub.

Usage:
    python scripts/new_vector.py tempo_stability_high
    python scripts/new_vector.py edge_case_zero_notes --category edge
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def create_vector(name: str, category: str) -> None:
    """Create a new vector file."""
    vectors_dir = REPO_ROOT / "fixtures" / "vectors"
    vectors_dir.mkdir(parents=True, exist_ok=True)

    vector_file = vectors_dir / f"{name}.json"

    if vector_file.exists():
        print(f"Vector already exists: {vector_file}")
        return

    # Template vector
    vector = {
        "_meta": {
            "name": name,
            "category": category,
            "description": "TODO: Describe what this vector tests",
            "created": "TODO: date",
        },
        "input": {
            "schema_id": "coach_context_packet_v1",
            "schema_version": "v1",
            "created_at_utc": "2026-01-21T12:00:00Z",
            "session_id": f"test-{name}",
            "request": {
                "kind": "groove_feedback",
                "template_id": "groove_feedback",
                "template_version": "1.0.0",
            },
            "evidence": {
                "groove_metrics": {
                    "tempo_stability": 0.8,
                    "beat_accuracy": 0.75,
                    "dynamics_range": 0.6,
                    "articulation_clarity": 0.7,
                    "phrase_coherence": 0.65,
                },
                "session_stats": {
                    "duration_seconds": 300,
                    "notes_played": 150,
                    "tempo_bpm": 120,
                    "time_signature": "4/4",
                },
            },
        },
        "expected": {
            "kind": "groove_feedback",
            "should_fail": False,
        },
    }

    vector_file.write_text(json.dumps(vector, indent=2) + "\n")
    print(f"Created: {vector_file}")
    print()
    print("Next steps:")
    print("1. Edit the vector input to match your test case")
    print("2. Run: python scripts/run_vectors.py --debug")
    print("3. If output is correct: python scripts/check_goldens.py --update")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create new acceptance vector")
    parser.add_argument("name", help="Vector name (snake_case)")
    parser.add_argument("--category", default="core", help="Category (core, edge, regression)")
    args = parser.parse_args()

    create_vector(args.name, args.category)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
