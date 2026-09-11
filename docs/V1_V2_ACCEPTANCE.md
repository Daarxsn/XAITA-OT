# XAITA-OT V1.0 / V2.0 Acceptance Record

## Scope

This document is the release acceptance record for the defined V1.0 Functional Baseline and V2.0 Research-Grade Prototype scope.

## V1.0 — Functional Baseline

**Status: COMPLETE / EXECUTED / FUNCTIONAL**

The V1 pipeline is implemented as a single analytical flow:

`SWaT input -> Detection -> BTAE -> BSS/EC/ECS -> ATT&CK for ICS -> MAS -> ACFM -> XAI -> Risk -> CTI`

Implemented acceptance areas:

- project/environment, configuration and versioning
- canonical OT, detection, episode, attribution and provenance objects with persistent identifiers
- telemetry cleaning, timestamp handling, missing values, encoding, normalization and temporal windows
- CNN, LSTM and CNN-LSTM detector implementations with DC and standard detection metrics
- BTAE temporal, asset, protocol, communication, sequence and behavior correlation with episode reconstruction and EC
- BSS, ECS, ATT&CK for ICS contextualization and MAS
- supporting/conflicting/unresolved evidence, belief, plausibility and uncertainty through ACFM-style fusion
- DC explicitly separated from AC
- feature/model and behavioral XAI, risk scoring, structured CTI and provenance links
- CLI, end-to-end execution and automated tests

### V1 execution evidence

The V1 pipeline was executed successfully against the repository's deterministic **SWaT-like demo fixture**. This validates software functionality and integration only. It is **not a real SWaT benchmark result**.

## V2.0 — Research-Grade Prototype

**Status: CORE IMPLEMENTATION COMPLETE / CONTROLLED EXECUTION VERIFIED**

Implemented acceptance areas:

- SWaT, BATADAL and TON-IoT dataset adapters
- common taxonomy and feature harmonization
- RF, CNN, LSTM and CNN-LSTM detector configurations
- fixed experiment configuration, seed management, metric/result storage and runtime tracking
- configurable BTAE correlation thresholds, temporal windows and correlation weights
- episode-aware processing
- DC, DC+BSS, DC+BSS+ECS, DC+BSS+ECS+MAS, WEF and ACFM attribution configurations
- reliability-weighted ACFM evidence classification and belief/plausibility uncertainty
- competing hypotheses
- SHAP explainability path
- perturbation fidelity and behavioral consistency helpers
- stage/risk explanation
- evidence IDs and backward provenance links
- standardized V2 execution and result collection

### V2 execution evidence

Controlled execution has been completed using the repository's deterministic demo fixtures for all three dataset adapters. The controlled validation path exercised the four detector configurations, six attribution configurations, and the final XAI/fidelity/provenance path. These fixtures are engineering validation data and **must not be represented as real SWaT, BATADAL or TON-IoT benchmark results**.

A prior five-seed demo execution also exercised the detector/attribution experiment matrix before the final XAI integration. The final XAI-integrated controlled execution was completed with one seed across all three demo datasets.

## Automated verification

The audited V2 codebase passed **22 automated tests** in the local acceptance run. The test suite covers canonical evidence objects, BTAE sequence/correlation behavior, episode-aware splitting, ECE bounds, the four-detector/six-attribution experiment contract, aggregation, attribution execution and V2 validation behavior.

## Acceptance boundary

This record confirms that V1/V2 are implemented and functionally executable as a research/engineering prototype. It does **not** claim:

- validated benchmark performance on the real SWaT, BATADAL or TON-IoT datasets;
- ground-truth actor-attribution accuracy where suitable attribution labels are unavailable;
- production certification or acceptance for deployment in a live OT/ICS environment.

Those are the next validation gates: **V3.0 Real-Dataset Research Validation**, followed by **V4.0 Production OT/ICS Deployment**.
