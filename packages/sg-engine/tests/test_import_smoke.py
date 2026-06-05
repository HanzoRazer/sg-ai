"""
Smoke test for sg-ai package import.

Sprint 40: Minimal pass condition for sg-ai in cross-repo tests.
"""
from __future__ import annotations


class TestImportSmoke:
    """Smoke tests for basic package imports."""

    def test_import_sg_engine(self) -> None:
        """sg_engine package must be importable."""
        import sg_engine  # noqa: F401

    def test_import_sg_engine_governance(self) -> None:
        """sg_engine.governance module must be importable."""
        from sg_engine import governance  # noqa: F401

    def test_sg_engine_has_version(self) -> None:
        """sg_engine should expose a version."""
        import sg_engine
        assert hasattr(sg_engine, "__version__") or hasattr(sg_engine, "VERSION")
