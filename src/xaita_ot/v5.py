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
    contract_id: str = "XAITA-OT-V5-DEV-1.0"
    supported_python: tuple[str, ...] = ("3.10", "3.11", "3.12", "3.13")
    cli_commands: tuple[str, ...] = ("demo", "synthetic-data", "validate-data", "real-experiment", "real-experiment-suite", "real-experiment-matrix", "real-experiment-statistics", "real-experiment-report", "attribution-evaluation", "experiment-manifest")
    api_routes: tuple[str, ...] = (
        "GET /health",
        "GET /ready",
        "GET /",
        "GET /v2/system",
        "GET /v2/capabilities",
        "GET /v2/ops/summary",
        "GET /v2/datasets",
        "GET /v2/benchmark",
        "POST /v2/experiment",
        "GET /v2/experiment/{job_id}",
        "POST /v1/analyze",
    )
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
            "contract_id": self.contract_id,
            "supported_python": list(self.supported_python),
            "cli_commands": list(self.cli_commands),
            "api_routes": list(self.api_routes),
            "pipeline": list(self.pipeline),
            "preserves_confidence_separation": self.preserves_confidence_separation,
            "preserves_provenance": self.preserves_provenance,
            "analyst_support_only": self.analyst_support_only,
        }


V5_CONTRACT = V5Contract()

__all__ = ["V5Contract", "V5_CONTRACT"]
