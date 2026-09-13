"""V5 capability and compatibility contract.

This module is intentionally dependency-free so it can be imported by the CLI,
API, and test layers without initializing models or external services.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class V5Contract:
    """Public compatibility contract for the V5 line."""

    major: int = 5
    minor: int = 1
    phase: str = "baseline-hardening"
    pipeline: tuple[str, ...] = (
        "observation",
        "detection",
        "episode",
        "context",
        "attribution",
        "explanation",
        "risk",
        "cti",
    )
    preserves_confidence_separation: bool = True
    preserves_provenance: bool = True
    analyst_support_only: bool = True

    @property
    def version(self) -> str:
        return f"{self.major}.{self.minor}"

    def as_dict(self) -> dict[str, object]:
        """Return a stable, JSON-serializable capability document."""
        return {
            "version": self.version,
            "phase": self.phase,
            "pipeline": list(self.pipeline),
            "preserves_confidence_separation": self.preserves_confidence_separation,
            "preserves_provenance": self.preserves_provenance,
            "analyst_support_only": self.analyst_support_only,
        }


V5_CONTRACT = V5Contract()

__all__ = ["V5Contract", "V5_CONTRACT"]
