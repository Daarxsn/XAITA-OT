from dataclasses import asdict
import math
from .schemas import AttributionAssessment


class AttributionValidationError(ValueError):
    """Raised when an attribution assessment violates its evidence semantics."""


def _clamp(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise AttributionValidationError("evidence values must be finite")
    if not 0.0 <= value <= 1.0:
        raise AttributionValidationError("evidence values must be in [0, 1]")
    return value


def assess(hypotheses, evidence, reliabilities, support_threshold=0.60, conflict_threshold=0.35):
    """Fuse heterogeneous evidence into belief/plausibility intervals.

    The result is an evidence interval, not a calibrated probability. Evidence
    in the unresolved band contributes neither support nor conflict; it keeps
    plausibility open. Belief and plausibility are normalized by total source
    reliability so strong evidence cannot automatically saturate at 1.0.
    """
    if not 0.0 < conflict_threshold < support_threshold < 1.0:
        raise ValueError("thresholds must satisfy 0 < conflict < support < 1")
    assessments = []
    seen = set()
    if not hypotheses:
        raise AttributionValidationError("at least one hypothesis is required")
    if not isinstance(evidence, dict) or not isinstance(reliabilities, dict):
        raise AttributionValidationError("evidence and reliabilities must be mappings")
    for source, reliability in reliabilities.items():
        _clamp(reliability)
    for hypothesis in hypotheses:
        if hypothesis in seen:
            raise AttributionValidationError(f"duplicate hypothesis: {hypothesis}")
        seen.add(hypothesis)
        vals = evidence.get(hypothesis, {})
        if not isinstance(vals, dict):
            raise AttributionValidationError(f"evidence for hypothesis {hypothesis} must be a mapping")
        supporting, conflicting, unresolved = [], [], []
        support_mass = conflict_mass = total_reliability = 0.0
        for source in sorted(vals):
            reliability = _clamp(reliabilities.get(source, 0.5))
            score = _clamp(vals[source])
            total_reliability += reliability
            item = {'source': source, 'value': score, 'reliability': reliability}
            if score >= support_threshold:
                support_mass += reliability * score
                supporting.append(item)
            elif score <= conflict_threshold:
                conflict_mass += reliability * (1.0 - score)
                conflicting.append(item)
            else:
                unresolved.append(item)
        denominator = max(total_reliability, 1e-12)
        belief = min(1.0, support_mass / denominator)
        plausibility = min(1.0, 1.0 - conflict_mass / denominator)
        if not unresolved and not conflicting:
            plausibility = belief
        assessments.append(AttributionAssessment(
            hypothesis, belief, max(belief, plausibility), supporting, conflicting, unresolved
        ))
    assessments.sort(key=lambda a: (-a.belief, -a.plausibility, a.hypothesis))
    return assessments


def validate_assessments(assessments):
    """Validate competing-hypothesis evidence semantics without calibration claims."""
    if not isinstance(assessments, list):
        raise AttributionValidationError("assessments must be a list")
    hypotheses = [a.hypothesis for a in assessments]
    if len(hypotheses) != len(set(hypotheses)):
        raise AttributionValidationError("hypothesis identifiers must be unique")
    for item in assessments:
        if not 0.0 <= item.belief <= item.plausibility <= 1.0:
            raise AttributionValidationError("belief/plausibility must satisfy 0 <= belief <= plausibility <= 1")
        if abs(item.interval_width - (item.plausibility - item.belief)) > 1e-12:
            raise AttributionValidationError("interval width is inconsistent")
        groups = [
            {entry["source"] for entry in item.supporting},
            {entry["source"] for entry in item.conflicting},
            {entry["source"] for entry in item.unresolved},
        ]
        if len(set().union(*groups)) != sum(len(group) for group in groups):
            raise AttributionValidationError("a source cannot appear in multiple evidence states")
    return True


def to_dict(a):
    d = asdict(a)
    d['interval_width'] = a.interval_width
    return d
