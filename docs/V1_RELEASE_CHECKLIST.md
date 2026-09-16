# XAITA-OT V1.0 Release Checklist

**Release:** V1.0 Functional Baseline  
**Status:** `LOCKED — FUNCTIONAL BASELINE COMPLETE`  
**Branch:** `main`

## Definition of completion

V1.0 is complete only for its declared functional-baseline scope when the implementation is executable, regression-tested, reproducible against the repository fixture, and its limitations are explicitly recorded.

This checklist must not be used to claim real-benchmark validation, production OT acceptance, or enterprise security approval.

## V1 checklist

| Area | Status | Evidence / boundary |
|---|---:|---|
| Core pipeline | ✅ | End-to-end analytical flow is implemented and documented. |
| Data preprocessing | ✅ | Cleaning, timestamps, missing values, encoding, normalization and temporal windows are implemented. |
| Detection implementation | ✅ | CNN, LSTM and CNN-LSTM paths and detection metrics are implemented. |
| Attribution logic | ✅ | BTAE, BSS, EC/ECS, MAS and uncertainty paths are implemented. |
| Explainability path | ✅ | Model/feature and behavioral explanation paths are implemented. |
| CLI workflow | ✅ | CLI and end-to-end execution path are present. |
| Automated testing | ✅ | Automated unit/integration/acceptance coverage is present and CI-validated. |
| Real benchmark validation | ⏸️ NOT A V1 COMPLETION CLAIM | Requires authorized real SWaT/BATADAL/TON-IoT data and belongs to V3. No synthetic fixture may be reported as benchmark evidence. |
| Production OT validation | ⏸️ NOT A V1 COMPLETION CLAIM | Requires live-environment validation, safety review, FAT/SAT and operational acceptance; belongs to V4. |
| Enterprise security validation | ⏸️ NOT A V1 COMPLETION CLAIM | Requires threat model, security assessment, dependency/SBOM review, hardening and enterprise acceptance; belongs to V4. |

## V1 execution boundary

V1 has been executed against the repository's deterministic SWaT-like demo fixture. This proves functionality and integration only. It does not prove performance on real benchmark datasets or production suitability.

## Lock decision

**V1 functional baseline is locked.** No V1 feature is to be reopened unless a reproducible defect is found.

The three non-functional/non-V1 gates remain explicitly open and are tracked as later release gates:

- Real benchmark validation → V3
- Production OT validation → V4
- Enterprise security validation → V4

Moving these rows to ✅ without the required evidence would be an inaccurate release claim.
