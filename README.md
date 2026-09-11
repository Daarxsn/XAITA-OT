# XAITA-OT

**Explainable AI-driven framework for threat attribution and cyber threat intelligence in Operational Technology security.**

This implementation follows the XAITA-OT research architecture: **Observation → Detection → Episode → Context → Attribution → Explanation → Risk → CTI**, with persistent evidence provenance and explicit **Detection Confidence (DC) ≠ Attribution Confidence (AC)**.

## V1.0 / V2.0 delivery status

**V1.0 Functional Baseline: COMPLETE / EXECUTED / FUNCTIONAL**

**V2.0 Research-Grade Prototype: CORE IMPLEMENTATION COMPLETE / CONTROLLED EXECUTION VERIFIED**

See [`docs/V1_V2_ACCEPTANCE.md`](docs/V1_V2_ACCEPTANCE.md) for the detailed acceptance record and execution boundary.

## V1.0 scope implemented

- repository/environment, dependencies, configuration and versioning
- canonical OT event, detection-event, attack-episode, attribution-hypothesis and CTI/provenance objects with evidence IDs
- SWaT-style ingestion, cleaning, timestamp normalization, missing-value handling, encoding, normalization and temporal windows
- CNN, LSTM and CNN-LSTM detector implementations
- detection confidence and precision/recall/F1/FPR/AUROC metrics
- BTAE temporal, asset, protocol, communication, sequence and behavior correlation
- attack-episode reconstruction and event-correlation strength (EC)
- BSS, ECS, ATT&CK for ICS context and MAS
- supporting/conflicting/unresolved evidence
- ACFM-style belief/plausibility interval and uncertainty
- explicit DC ≠ AC separation
- SHAP/model and behavioral/stage explanations
- risk scoring
- structured CTI and provenance links
- end-to-end CLI and automated tests

## V2.0 scope implemented

- SWaT, BATADAL and TON-IoT adapters
- common feature taxonomy and harmonization
- Random Forest, CNN, LSTM and CNN-LSTM configurations
- controlled experiment configuration, seeds, metric/result storage and runtime logging
- configurable BTAE thresholds, temporal windows and asset/protocol/sequence/behavior weights
- episode-aware processing
- six attribution configurations: DC, DC+BSS, DC+BSS+ECS, DC+BSS+ECS+MAS, ACFM and WEF
- reliability-weighted ACFM with competing hypotheses and uncertainty
- SHAP, perturbation fidelity and behavioral consistency paths
- stage/risk explanations
- evidence IDs and backward provenance
- unified V2 execution and standardized result collection
- FastAPI analyst/API surface and research dashboard

## Verification boundary

The audited implementation passed **22 automated tests** in the local acceptance run. V1 was executed successfully against the deterministic **SWaT-like demo fixture**. V2 controlled execution was completed across the three deterministic dataset fixtures, including the four detector configurations, six attribution configurations, and the final XAI/fidelity/provenance path.

These fixtures validate implementation and integration only. They are **not real SWaT, BATADAL or TON-IoT benchmark datasets**, and their outputs must not be reported as benchmark performance. Real benchmark validation is the next V3 research gate.

## Important deployment boundary

XAITA-OT is an **analyst-support security analytics system**. It does not issue PLC/RTU/SCADA control commands and does not autonomously perform safety-critical OT actions. V1/V2 completion does not constitute certification or production acceptance for a live OT/ICS environment.

## Quick start (Windows PowerShell)

```powershell
cd C:\path\to\xaita-ot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python -m xaita_ot.cli synthetic-data
python -m xaita_ot.cli demo
python run_api.py
```

API: `http://127.0.0.1:8080/docs`

## Dataset policy

Actual SWaT, BATADAL and TON-IoT benchmark files must be supplied by the researcher under their applicable dataset terms. Do not place proprietary or restricted benchmark files in source control.

## Next targets

**V3.0 — Real-Dataset Research Validation:** authorized real SWaT/BATADAL/TON-IoT experiments, statistical evaluation, attribution evaluation, ablation/sensitivity/cross-environment analysis, XAI validation and reproducible research artifacts.

**V4.0 — Production OT/ICS Deployment:** secure deployment, authentication/RBAC, TLS, secrets, OT integration, auditability, performance/load testing, security assessment, model lifecycle, backup/recovery, OT safety validation, FAT/SAT and operational acceptance.

## Research integrity

No benchmark result should be presented as achieved unless it was produced by a reproducible run against the specified real dataset and configuration. Synthetic/demo outputs are for functionality validation only.
