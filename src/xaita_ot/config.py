from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import yaml


class ModelConfig(BaseModel):
    input_features: int = 16
    window_size: int = 32
    cnn_channels: int = 32
    lstm_hidden: int = 64
    dropout: float = 0.2
    epochs: int = 8
    batch_size: int = 128
    learning_rate: float = 1e-3


class CorrelationConfig(BaseModel):
    temporal_window_seconds: float = 60.0
    threshold: float = 0.55
    weights: dict[str, float] = Field(default_factory=lambda: {
        "temporal": 0.30, "asset": 0.20, "protocol": 0.15,
        "communication": 0.15, "behavior": 0.20,
    })

    @field_validator("weights")
    @classmethod
    def weights_sum_to_one(cls, value):
        required = {"temporal", "asset", "protocol", "communication", "behavior"}
        if set(value) != required:
            raise ValueError(f"correlation weights must contain exactly {sorted(required)}")
        if any(v < 0 for v in value.values()):
            raise ValueError("correlation weights must be non-negative")
        if abs(sum(value.values()) - 1.0) > 1e-6:
            raise ValueError("correlation weights must sum to 1.0")
        return value


class AttributionConfig(BaseModel):
    reliability: dict[str, float] = Field(default_factory=lambda: {
        "DC": 0.70, "BSS": 0.80, "ECS": 0.85, "EC": 0.80, "MAS": 0.65
    })
    ambiguity_margin: float = 0.08
    support_threshold: float = 0.60
    conflict_threshold: float = 0.35
    methods: list[str] = Field(default_factory=lambda: [
        "DC", "DC+BSS", "DC+BSS+ECS", "DC+BSS+ECS+MAS", "WEF", "ACFM"
    ])
    hypothesis_profiles: dict[str, dict[str, float]] = Field(default_factory=lambda: {
        "H1": {"DC": 1.00, "BSS": 1.00, "ECS": 1.00, "EC": 1.00, "MAS": 1.00},
        "H2": {"DC": 0.95, "BSS": 1.00, "ECS": 0.80, "EC": 0.90, "MAS": 0.90},
        "H3": {"DC": 0.85, "BSS": 0.80, "ECS": 0.70, "EC": 0.75, "MAS": 0.80},
    })


class RiskConfig(BaseModel):
    weights: dict[str, float] = Field(default_factory=lambda: {
        "severity": 0.30, "operational_impact": 0.30, "criticality": 0.25, "attribution": 0.15
    })


class ExperimentConfig(BaseModel):
    seeds: list[int] = Field(default_factory=lambda: [42, 43, 44, 45, 46])
    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    episode_aware: bool = True
    xai_background_samples: int = 16
    xai_explanation_samples: int = 16


class AppConfig(BaseModel):
    seed: int = 42
    model: ModelConfig = Field(default_factory=ModelConfig)
    correlation: CorrelationConfig = Field(default_factory=CorrelationConfig)
    attribution: AttributionConfig = Field(default_factory=AttributionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    experiment: ExperimentConfig = Field(default_factory=ExperimentConfig)
    attack_label_column: str = "label"
    timestamp_column: str = "timestamp"
    output_dir: str = "artifacts"


def load_config(path: str | Path = "configs/default.yaml") -> AppConfig:
    p = Path(path)
    if not p.exists():
        return AppConfig()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)
