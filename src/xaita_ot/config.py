from pathlib import Path
from pydantic import BaseModel, Field
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

class AttributionConfig(BaseModel):
    reliability: dict[str, float] = Field(default_factory=lambda: {
        "DC": 0.70, "BSS": 0.80, "ECS": 0.85, "EC": 0.80, "MAS": 0.65
    })
    ambiguity_margin: float = 0.08

class RiskConfig(BaseModel):
    weights: dict[str, float] = Field(default_factory=lambda: {
        "severity": 0.30, "operational_impact": 0.30, "criticality": 0.25, "attribution": 0.15
    })

class AppConfig(BaseModel):
    seed: int = 42
    model: ModelConfig = ModelConfig()
    correlation: CorrelationConfig = CorrelationConfig()
    attribution: AttributionConfig = AttributionConfig()
    risk: RiskConfig = RiskConfig()
    attack_label_column: str = "label"
    timestamp_column: str = "timestamp"
    output_dir: str = "artifacts"

def load_config(path: str | Path = "configs/default.yaml") -> AppConfig:
    p = Path(path)
    if not p.exists():
        return AppConfig()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)
