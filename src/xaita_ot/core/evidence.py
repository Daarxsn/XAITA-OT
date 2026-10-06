"""V5.2 evidence-state validation.

Evidence is explicit, bounded and auditable. This module validates the payload
inside supporting, conflicting and unresolved evidence groups without turning
belief/plausibility into calibrated probabilities.
"""

from __future__ import annotations

import math
from typing import Any


class EvidenceValidationError(ValueError):
    """Raised when evidence-state data violates the V5.2 contract."""


STATES = ("supporting", "conflicting", "unresolved")


def _finite_unit(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise EvidenceValidationError(f"{field} must be numeric") from exc
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise EvidenceValidationError(f"{field} must be finite and in [0, 1]")
    return result


def validate_evidence_groups(groups: dict[str, Any]) -> bool:
    """Validate supporting/conflicting/unresolved evidence entries.

    Every entry needs a stable source, bounded value and bounded reliability.
    A source may occur in exactly one state. Extra fields are retained rather
    than rejected so evidence producers remain forward-compatible.
    """
    if not isinstance(groups, dict):
        raise EvidenceValidationError("evidence groups must be a mapping")

    unknown = set(groups) - set(STATES)
    if unknown:
        raise EvidenceValidationError(f"unknown evidence states: {sorted(unknown)}")

    seen: set[str] = set()
    for state in STATES:
        entries = groups.get(state, [])
        if not isinstance(entries, list):
            raise EvidenceValidationError(f"{state} evidence must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise EvidenceValidationError(f"{state} evidence entries must be mappings")
            source = entry.get("source")
            if not isinstance(source, str) or not source.strip():
                raise EvidenceValidationError(f"{state} evidence requires a non-empty source")
            source = source.strip()
            if source in seen:
                raise EvidenceValidationError(
                    f"evidence source appears in multiple states: {source}"
                )
            seen.add(source)
            _finite_unit(entry.get("value"), f"{state}.value")
            _finite_unit(entry.get("reliability"), f"{state}.reliability")
    return True


def validate_attribution_evidence(assessment: Any) -> bool:
    """Validate one attribution assessment's evidence payload."""
    groups = {
        state: getattr(assessment, state, None)
        for state in STATES
    }
    validate_evidence_groups(groups)
    belief = _finite_unit(getattr(assessment, "belief", None), "belief")
    plausibility = _finite_unit(getattr(assessment, "plausibility", None), "plausibility")
    if belief > plausibility:
        raise EvidenceValidationError("belief cannot exceed plausibility")
    width = getattr(assessment, "interval_width", None)
    if width is None or abs(float(width) - (plausibility - belief)) > 1e-12:
        raise EvidenceValidationError("interval width is inconsistent")
    return True
