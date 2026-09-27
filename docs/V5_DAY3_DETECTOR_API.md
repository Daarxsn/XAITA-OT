# XAITA-OT v5 — Day 3 Detector/API Lock

**Baseline:** `main` after Day 2.  
**Scope:** detector execution correctness and Research Lab/API contract.

## Completed

- The experiment API now passes the selected detector into the training pipeline instead of training all four detectors and discarding three results.
- Detector aliases are normalized consistently: RF/random forest → `random_forest`; CNN → `cnn`; LSTM → `lstm`; CNN-LSTM → `cnn_lstm`.
- The training layer accepts an explicit detector list and executes only the requested detector(s).
- Validation-only threshold selection remains in place; test metrics are calculated only after threshold selection.
- Random seeds are applied before experiment execution and are carried into the detector training path.
- Experiment metadata records the detector and split protocol.
- Synthetic-event-order TON-IoT runs continue to use group-stratified splitting; timestamped OT datasets continue to use chronological, episode-aware splitting.
- Insufficient usable data now fails explicitly rather than producing an ambiguous run.
- The API returns the selected detector's metrics plus the complete metrics object for transparency.
- API schema version for targeted runs is `XAITA-OT-V2-RUN-1.2`.

## Locked detector contract

`SWaT | BATADAL | TON-IoT` × `RF | CNN | LSTM | CNN-LSTM` × explicit seed

Each run must produce:

- experiment ID
- dataset
- detector
- seed
- start time
- runtime
- train/validation/test row counts
- train/validation/test window counts
- detector metrics
- dataset file provenance
- split protocol

## Acceptance boundary

A successful HTTP response proves that the selected detector path executed and returned structured metrics. It does **not** by itself constitute an official benchmark claim. Official benchmark results remain the separately versioned research artifacts with their documented protocol.

## Day 3 exit

Detector selection and API execution semantics are locked. Remaining release work belongs to end-to-end pipeline, attribution/XAI/risk/CTI acceptance and deployment QA, not another detector-selection implementation.
