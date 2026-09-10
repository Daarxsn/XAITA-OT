# Paper-to-Implementation Mapping

| Paper concept | Implementation |
|---|---|
| E observations | telemetry ingestion + DetectionEvent |
| CNN-LSTM | `models/cnn_lstm.py` |
| BTAE | `core/btae.py` |
| BSS | `pipeline/engine.py` behavioral signal |
| ECS | `core/context.py` |
| EC | `AttackEpisode.correlation_strength` |
| MAS | engine multi-attribute signal |
| ACFM | `core/attribution.py` |
| Bel/Pl uncertainty | `AttributionAssessment` |
| XAI | `explain/xai.py` |
| Risk | `core/risk.py` |
| Evidence-linked CTI | `cti/generator.py` |
| Human validation | CTI `human_validation_required=true` |
| No autonomous OT action | CTI `autonomous_ot_action=false` |
