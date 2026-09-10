# XAITA-OT

**Explainable AI-driven framework for threat attribution and cyber threat intelligence in Operational Technology security.**

This implementation follows the research architecture in the supplied XAITA-OT paper: **Observation → Detection → Episode → Context → Attribution → Explanation → Risk → CTI**, with persistent evidence provenance and explicit **Detection Confidence (DC) ≠ Attribution Confidence (AC)**.

## What is implemented

- OT telemetry CSV ingestion and semantic harmonization
- Leakage-conscious preprocessing/window construction
- CNN-LSTM detection model (PyTorch; CPU/GPU auto-selection)
- Structured detection evidence objects
- BTAE event correlation and attack-episode reconstruction
- BSS behavioral similarity signal
- ECS / configurable MITRE ATT&CK for ICS contextualization
- EC event-correlation strength
- MAS multi-attribute signal
- ACFM-style reliability-weighted supporting/conflicting/unresolved evidence
- Belief/plausibility attribution intervals
- Four-level XAI evidence chain
- Operational risk scoring
- Provenance-preserving CTI JSON output
- FastAPI analyst/API surface
- Deterministic synthetic smoke dataset and tests
- Configurable mappings and weights

## Important deployment boundary

The module is an **analyst-support security analytics system**. It does not issue PLC/RTU/SCADA control commands and does not autonomously perform safety-critical OT actions. Production deployment requires environment-specific validation, threat modeling, secure integration, access control, monitoring, performance testing, and organizational approval.

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

## SWaT / BATADAL / TON-IoT

The repository provides the common ingestion/harmonization interfaces, but the actual benchmark files must be supplied by the researcher under their applicable dataset terms. Do not place proprietary or restricted datasets in source control. Dataset-specific adapters should map native columns into the semantic taxonomy before model fitting.

## Four-day build track

**V1 Functional Baseline:** detection + BTAE + BSS/ECS/EC + ACFM + XAI + risk + CTI + API.

**V2 Research Validation:** SWaT benchmark runs, leakage checks, baseline comparisons, calibration/ECE, ablation and sensitivity tooling, BATADAL/TON-IoT adapters.

**V3 Product Hardening:** analyst dashboard, RBAC/authentication integration, structured audit logs, STIX/TAXII export, Docker deployment, performance/load testing, security hardening, documentation and release packaging.

## Research integrity

No benchmark result in this repository should be presented as an achieved result unless it was produced by a reproducible run against the specified dataset and configuration. Synthetic smoke outputs are for functionality validation only.
