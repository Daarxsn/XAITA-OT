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

The implementation is covered by automated unit, integration, smoke, and acceptance tests executed in CI. V1 was executed successfully against the deterministic **SWaT-like demo fixture**. V2 controlled execution was completed across the three deterministic dataset fixtures, including the four detector configurations, six attribution configurations, and the final XAI/fidelity/provenance path.

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

## Real benchmark validation

Researcher-supplied SWaT, BATADAL and TON-IoT files are validated without storing
raw data in Git. The validator records CSV schema, timestamps, labels, row counts,
missing/invalid values, SHA-256 file identity and a deterministic manifest digest.

For one dataset:

```powershell
xaita validate-data --dataset SWaT --root data/raw/swat
xaita validate-data --dataset BATADAL --root data/raw/batadal
xaita validate-data --dataset TON-IoT --root data/raw/ton_iot
```

For all configured datasets:

```powershell
python scripts/v5_validate_local_datasets.py
```

A validation result of `ready=false` or exit code `2` means the files require
review; it is not silently converted into benchmark evidence. A passing manifest
only validates the dataset files and metadata. It does not itself constitute model
performance, cross-environment generalization, security certification or customer
OT acceptance.

For a validated real benchmark file, run one detector with an auditable result envelope:

```powershell
xaita real-experiment --dataset SWaT --csv data/raw/swat/<benchmark-file>.csv --detector random_forest --seed 42
```

To execute all four supported detectors against the same validated file and seed:

```powershell
xaita real-experiment-suite --dataset SWaT --csv data/raw/swat/<benchmark-file>.csv --seed 42
```

The suite runs `random_forest`, `cnn`, `lstm` and `cnn_lstm` in deterministic order. Each completed detector retains an audit envelope; the suite records completed/failed detectors, configuration identity and a deterministic suite fingerprint. Any detector failure makes the suite `failed`, so partial execution is not presented as four-detector acceptance evidence.

To execute the same four-detector suite across all three configured real benchmark families:

```powershell
xaita real-experiment-matrix --swat-csv <swat.csv> --batadal-csv <batadal.csv> --toniot-csv <toniot.csv> --seed 42
```

The matrix validates and executes `SWaT`, `BATADAL` and `TON-IoT` in deterministic order, with `random_forest`, `cnn`, `lstm` and `cnn_lstm` for each dataset. Each dataset retains its complete suite result or an explicit failure record. The matrix is accepted only when all requested datasets complete all requested detectors, and its fingerprint binds dataset order, detector order, seed, status and configuration.

For repeated real benchmark evaluation across multiple seeds:

```powershell
xaita real-experiment-statistics --swat-csv <swat.csv> --batadal-csv <batadal.csv> --toniot-csv <toniot.csv> --seed 42 --seed 43 --seed 44 --confidence 0.95
```

The statistical runner requires at least two unique seeds, executes the Day 23 matrix for each seed, and reports per-dataset/per-detector metric mean, sample standard deviation, Student-t confidence intervals, and paired detector comparisons across matched seeds. Failed matrix runs are retained and prevent statistical acceptance. These statistics are descriptive/research evaluation outputs; they do not establish benchmark superiority, significance beyond the reported tests, generalization, or production OT acceptance.

The result records the validated file hash, dataset, detector, seed, split protocol,
configuration digest and a deterministic reproducibility fingerprint. Execution is
blocked when the input fails the validation gate. Raw benchmark files are never
written by the command.

## Dataset policy

Actual SWaT, BATADAL and TON-IoT benchmark files must be supplied by the researcher under their applicable dataset terms. Do not place proprietary or restricted benchmark files in source control.

## Next targets

**V3.0 — Real-Dataset Research Validation:** authorized real SWaT/BATADAL/TON-IoT experiments, statistical evaluation, attribution evaluation, ablation/sensitivity/cross-environment analysis, XAI validation and reproducible research artifacts.

**V4.0 — Production OT/ICS Deployment:** secure deployment, authentication/RBAC, TLS, secrets, OT integration, auditability, performance/load testing, security assessment, model lifecycle, backup/recovery, OT safety validation, FAT/SAT and operational acceptance.

## Research integrity

No benchmark result should be presented as achieved unless it was produced by a reproducible run against the specified real dataset and configuration. Synthetic/demo outputs are for functionality validation only.
