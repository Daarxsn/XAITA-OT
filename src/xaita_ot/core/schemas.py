from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class DetectionEvent:
    event_id: str
    timestamp: datetime
    asset: str
    protocol: str
    label: str
    detection_confidence: float
    features: dict[str, float] = field(default_factory=dict)

@dataclass
class AttackEpisode:
    episode_id: str
    events: list[DetectionEvent]
    correlation_strength: float
    stages: list[str] = field(default_factory=list)

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
class CTIProduct:
    incident_id: str
    detection: dict[str, Any]
    behavior: dict[str, Any]
    context: dict[str, Any]
    attribution: dict[str, Any]
    xai: dict[str, Any]
    risk: dict[str, Any]
    provenance: list[str]
