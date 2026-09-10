from dataclasses import asdict
from .schemas import AttributionAssessment


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


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
    for hypothesis in hypotheses:
        vals = evidence.get(hypothesis, {})
        supporting, conflicting, unresolved = [], [], []
        support_mass = conflict_mass = total_reliability = 0.0
        for source, raw_value in vals.items():
            reliability = _clamp(reliabilities.get(source, 0.5))
            score = _clamp(raw_value)
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
    assessments.sort(key=lambda a: (a.belief, a.plausibility), reverse=True)
    return assessments


def to_dict(a):
    d = asdict(a)
    d['interval_width'] = a.interval_width
    return d
