from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml
import math


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
        "temporal": 0.25, "asset": 0.15, "protocol": 0.10,
        "communication": 0.10, "sequence": 0.20, "behavior": 0.20,
    })

    @field_validator("weights")
    @classmethod
    def weights_sum_to_one(cls, value):
        required = {"temporal", "asset", "protocol", "communication", "sequence", "behavior"}
        if set(value) != required:
            raise ValueError(f"correlation weights must contain exactly {sorted(required)}")
        if any(not math.isfinite(float(v)) or float(v) < 0 for v in value.values()):
            raise ValueError("correlation weights must be finite and non-negative")
        if abs(sum(float(v) for v in value.values()) - 1.0) > 1e-6:
            raise ValueError("correlation weights must sum to 1.0")
        return {str(k): float(v) for k, v in value.items()}

    @model_validator(mode="after")
    def validate_correlation_parameters(self):
        if not math.isfinite(self.temporal_window_seconds) or self.temporal_window_seconds <= 0:
            raise ValueError("temporal_window_seconds must be finite and positive")
        if not math.isfinite(self.threshold) or not 0.0 <= self.threshold <= 1.0:
            raise ValueError("correlation threshold must be finite and in [0, 1]")
        return self


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

    @field_validator("reliability")
    @classmethod
    def reliability_valid(cls, value):
        required = {"DC", "BSS", "ECS", "EC", "MAS"}
        if set(value) != required:
            raise ValueError(f"attribution reliability must contain exactly {sorted(required)}")
        if any(not math.isfinite(float(v)) or not 0.0 <= float(v) <= 1.0 for v in value.values()):
            raise ValueError("attribution reliability values must be finite and in [0, 1]")
        return {str(k): float(v) for k, v in value.items()}

    @field_validator("methods")
    @classmethod
    def methods_valid(cls, value):
        allowed = {"DC", "DC+BSS", "DC+BSS+ECS", "DC+BSS+ECS+MAS", "WEF", "ACFM"}
        if not value or len(value) != len(set(value)) or not set(value).issubset(allowed):
            raise ValueError("attribution methods must be unique supported configurations")
        return value

    @model_validator(mode="after")
    def thresholds_valid(self):
        if not 0.0 < self.conflict_threshold < self.support_threshold < 1.0:
            raise ValueError("attribution thresholds must satisfy 0 < conflict < support < 1")
        if not math.isfinite(self.ambiguity_margin) or not 0.0 <= self.ambiguity_margin < 1.0:
            raise ValueError("ambiguity_margin must be finite and in [0, 1)")
        return self


class RiskConfig(BaseModel):
    weights: dict[str, float] = Field(default_factory=lambda: {
        "severity": 0.30, "operational_impact": 0.30, "criticality": 0.25, "attribution": 0.15
    })

    @field_validator("weights")
    @classmethod
    def risk_weights_valid(cls, value):
        required = {"severity", "operational_impact", "criticality", "attribution"}
        if set(value) != required:
            raise ValueError(f"risk weights must contain exactly {sorted(required)}")
        if any(not math.isfinite(float(v)) or not 0.0 <= float(v) <= 1.0 for v in value.values()):
            raise ValueError("risk weights must be finite and in [0, 1]")
        if abs(sum(float(v) for v in value.values()) - 1.0) > 1e-6:
            raise ValueError("risk weights must sum to 1.0")
        return {str(k): float(v) for k, v in value.items()}


class ExperimentConfig(BaseModel):
    seeds: list[int] = Field(default_factory=lambda: [42, 43, 44, 45, 46])
    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    episode_aware: bool = True
    threshold_metric: str = "f1"
    max_rf_train_windows: int = 50000
    max_neural_train_windows: int = 100000
    rf_n_jobs: int = 2
    xai_background_samples: int = 16
    xai_explanation_samples: int = 16

    @field_validator("threshold_metric")
    @classmethod
    def threshold_metric_allowed(cls, value):
        if value not in {"f1", "balanced_accuracy"}:
            raise ValueError("threshold_metric must be 'f1' or 'balanced_accuracy'")
        return value

    @field_validator("seeds")
    @classmethod
    def seeds_valid(cls, value):
        if not value or len(value) != len(set(value)) or any(int(seed) < 0 for seed in value):
            raise ValueError("experiment seeds must be unique non-negative integers")
        return [int(seed) for seed in value]

    @model_validator(mode="after")
    def validate_experiment_parameters(self):
        if not 0.0 < self.train_fraction < 1.0 or not 0.0 < self.validation_fraction < 1.0:
            raise ValueError("train_fraction and validation_fraction must be in (0, 1)")
        if self.train_fraction + self.validation_fraction >= 1.0:
            raise ValueError("train_fraction and validation_fraction must sum to less than 1")
        if self.max_rf_train_windows <= 0 or self.max_neural_train_windows <= 0:
            raise ValueError("training window limits must be positive")
        if self.rf_n_jobs == 0 or self.xai_background_samples <= 0 or self.xai_explanation_samples <= 0:
            raise ValueError("rf_n_jobs cannot be zero and XAI sample limits must be positive")
        return self


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
    if not p.is_absolute() and not p.exists():
        project_root = Path(__file__).resolve().parents[2]
        candidate = project_root / p
        if candidate.exists():
            p = candidate
    if not p.exists():
        return AppConfig()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)
