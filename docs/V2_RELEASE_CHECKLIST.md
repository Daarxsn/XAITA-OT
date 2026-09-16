# XAITA-OT V2.0 Release Checklist

**Release:** V2.0 Research-Grade Prototype  
**Status:** `LOCKED — CORE IMPLEMENTATION COMPLETE / CONTROLLED EXECUTION VERIFIED`  
**Branch:** `main`

## Definition of completion

V2.0 is complete for its declared research-prototype scope when the dataset-adapter architecture, detector/attribution matrices, controlled experiment runner, result storage, explainability and provenance paths execute reproducibly against the repository's deterministic fixtures.

V2.0 does **not** claim real benchmark performance, statistical research validation, cross-environment generalization or production performance acceptance. Those require separate evidence and are tracked as later gates.

## V2 checklist

| Area | Status | Evidence / boundary |
|---|---:|---|
| Dataset adapter architecture | ✅ | SWaT, BATADAL and TON-IoT adapter paths are implemented and exercised against deterministic fixtures. |
| Detector matrix | ✅ | RF, CNN, LSTM and CNN-LSTM configurations are implemented and covered by the controlled execution contract. |
| Attribution matrix | ✅ | DC, DC+BSS, DC+BSS+ECS, DC+BSS+ECS+MAS, WEF and ACFM configurations are implemented. |
| Controlled experiment execution | ✅ | Fixed configuration, seed handling, episode-aware processing, thresholds and correlation weights are implemented. |
| Result storage | ✅ | Standardized metrics, result collection and runtime tracking are implemented. |
| Explainability path | ✅ | SHAP, perturbation fidelity, behavioral consistency and stage/risk explanation paths are implemented. |
| Provenance | ✅ | Evidence IDs and backward provenance links are implemented. |
| Demo validation | ✅ | Controlled execution was completed across the three deterministic dataset fixtures. |
| Real dataset validation | ⏸️ OPEN — V3 GATE | Requires authorized real SWaT, BATADAL and TON-IoT datasets, dataset versions/hashes and reproducible runs. |
| Statistical research evaluation | ⏸️ OPEN — V3 GATE | Requires statistical evaluation, confidence intervals, baselines, ablation and sensitivity analysis. |
| Cross-environment validation | ⏸️ OPEN — V3 GATE | Requires evaluation across environments/datasets and documented generalization limits. |
| Production performance testing | ⏸️ OPEN — V4 GATE | Requires representative load tests, latency/throughput targets, resource limits and operational acceptance. |

## V2 execution evidence

The V2 controlled path was executed using deterministic demo fixtures for all three dataset adapters. The execution exercised the four detector configurations, six attribution configurations and the integrated XAI/fidelity/provenance path.

These fixtures validate implementation and integration only. They are **not** the real SWaT, BATADAL or TON-IoT benchmark datasets, and their outputs must not be reported as benchmark performance.

## Lock decision

**V2 core research-prototype scope is locked.** No V2 feature is to be reopened unless a reproducible defect is found.

The four non-V2 completion gates remain explicitly open:

- Real dataset validation → V3
- Statistical research evaluation → V3
- Cross-environment validation → V3
- Production performance testing → V4

Moving these rows to ✅ without the required evidence would be an inaccurate release claim.
