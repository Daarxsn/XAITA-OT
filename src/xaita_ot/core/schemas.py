from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class OTEvent:
    """Canonical raw OT observation used as the provenance root."""
    event_id: str
    timestamp: datetime
    asset: str = "unknown"
    protocol: str = "unknown"
    source: str = "unknown"
    destination: str = "unknown"
    features: dict[str, float] = field(default_factory=dict)
    provenance: list[str] = field(default_factory=list)


@dataclass
class DetectionEvent:
    event_id: str
    timestamp: datetime
    asset: str
    protocol: str
    label: str
    detection_confidence: float
    features: dict[str, float] = field(default_factory=dict)
    source: str = "unknown"
    destination: str = "unknown"
    observation_id: str | None = None


@dataclass
class AttackEpisode:
    episode_id: str
    events: list[DetectionEvent]
    correlation_strength: float
    stages: list[str] = field(default_factory=list)
    correlation_edges: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AttributionHypothesis:
    """Explicit attribution hypothesis definition and evidence requirements."""
    hypothesis_id: str
    name: str
    description: str
    evidence_requirements: dict[str, float] = field(default_factory=dict)
    status: str = "candidate"


@dataclass
class AttributionAssessment:
    hypothesis: str
    belief: float
    plausibility: float
    supporting: list[dict[str, Any]]
    conflicting: list[dict[str, Any]]
    unresolved: list[dict[str, Any]]

    @property
    def interval_width(self) -> float:
        return max(0.0, self.plausibility - self.belief)


@dataclass
class ProvenanceRecord:
    evidence_id: str
    source_type: str
    source_ref: str
    created_at: datetime
    parent_ids: list[str] = field(default_factory=list)


@dataclass
class CTIProduct:
    incident_id: str
    detection: dict[str, Any]
    behavior: dict[str, Any]
    context: dict[str, Any]
    attribution: dict[str, Any]
    xai: dict[str, Any]
    risk: dict[str, Any]
    provenance: list[str]
