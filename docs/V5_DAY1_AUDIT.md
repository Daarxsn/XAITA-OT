# XAITA-OT v5 — Day 1 Repository Audit & Scope Lock

**Audit date:** 2026-09-27  
**Baseline commit:** `060699786af937a2cfc5e7bc9817d29a63e9c53e`  
**Package version:** `0.5.1`  
**V5 contract:** `5.1 / baseline-hardening`

## 1. Purpose

Day 1 establishes a single source of truth for completion of XAITA-OT v5. This document freezes the delivery scope and records what is already present versus what remains to be proven, corrected, hardened, or documented.

This is a **scope lock**, not a claim that the product is already release-ready.

## 2. Product contract locked for v5

XAITA-OT v5 is an analyst-support OT/ICS security analytics platform implementing the evidence-continuous flow:

`Observation → Detection → Episode → Context → Attribution → Explanation → Risk → CTI`

The v5 contract preserves:

- Detection Confidence (DC) distinct from Attribution Confidence (AC)
- evidence provenance
- analyst-support-only operation
- no autonomous PLC/RTU/SCADA control actions
- reproducible research/benchmark separation from live/local experiments

## 3. Repository baseline

The current `main` branch baseline is commit `0606997` (`fix: expose live multi-dataset research controls`). Recent product commits include the OT SOC dashboard redesign, analyst workflow alignment, benchmark seed selector, Research Lab redesign, TON-IoT benchmark integration, and multi-dataset live controls.

The repository contains dedicated modules for API, CLI/configuration, canonical core objects, CTI, datasets/adapters, explainability, models, pipeline processing, and the V5 compatibility contract.

The package declares Python `>=3.10,<3.14`, version `0.5.1`, and dependencies covering NumPy, pandas, scikit-learn, SciPy, joblib, PyYAML, Pydantic, FastAPI/Uvicorn, PyTorch and SHAP.

## 4. Capability inventory

| Capability | Day 1 finding | v5 status |
|---|---|---|
| OT SOC dashboard | Implemented in current main line | Existing; final QA required |
| Research Lab | Implemented with dataset/model/seed controls | Existing; final QA required |
| SWaT support | Adapter/configuration and live dataset path exist | Real-data execution validation required |
| BATADAL support | Adapter/configuration and live dataset path exist | Real-data execution validation required |
| TON-IoT support | Adapter/configuration and live dataset path exist | Real-data execution validation required |
| RF/CNN/LSTM/CNN-LSTM | Implemented | Execution/contract validation required |
| Benchmark seeds | Configuration includes 42–46; UI controls exist | Final benchmark/live separation QA required |
| Detection | Implemented | End-to-end acceptance required |
| Episode/correlation | Implemented | End-to-end acceptance required |
| ATT&CK/context | Mapping configuration exists | Representative behavior mapping validation required |
| Attribution | DC/BSS/ECS/MAS/WEF/ACFM paths exist | Uncertainty and evidence validation required |
| XAI | SHAP/perturbation/behavioral paths exist | Fidelity and usability validation required |
| Risk | Implemented | End-to-end acceptance required |
| CTI/STIX | Structured CTI/provenance artifacts exist | End-to-end acceptance required |
| API | FastAPI analyst/API surface exists | Full v5 API acceptance required |
| Dashboard/API dataset status | `/v2/datasets` and research controls exist | Final UI/API contract QA required |
| Installation | Windows quick-start and CI installation workflows exist | Clean-machine reproduction required |
| Automated tests | Broad V1–V3 test/CI coverage exists | Full current v5 suite must pass before release |
| Dependency audit | `pip-audit` is part of CI | Current CI result must be verified before release |
| Production hardening | Authentication/header controls and Docker support exist | Security/load/deployment acceptance remains |
| Documentation | V1/V2 acceptance and README exist | v5 user/admin/release documentation remains |

## 5. Known delivery gaps carried into the v5 execution backlog

### P0 — Correctness / functional completion

1. Execute and validate the complete real-data path for SWaT, BATADAL and TON-IoT on the Windows delivery environment.
2. Finalize SWaT schema/label handling across the supplied heterogeneous CSV files; do not assume every `Attack State` value is binary `True/False`.
3. Validate BATADAL end-to-end using the authorized dataset and existing attack metadata boundary.
4. Validate TON-IoT end-to-end for the selected network/IoT research paths.
5. Validate all four detector contracts through the API/Research Lab.
6. Verify the complete pipeline from detection through episode, context, attribution, explanation, risk and CTI.
7. Resolve and regression-test unresolved-evidence uncertainty behavior so unresolved evidence cannot produce unjustified certainty.
8. Validate representative behavior-to-ATT&CK mappings and ensure missing mappings are explicitly represented rather than silently omitted.

### P1 — Company usability / robustness

9. Remove remaining terminal-only operational dependencies from normal analyst/researcher workflows.
10. Ensure missing, corrupt, unsupported, empty and insufficient datasets produce actionable UI/API errors.
11. Protect resource-intensive local experiments from accidental duplicate/concurrent execution and expose execution state.
12. Validate configuration and dataset path resolution without developer-specific absolute paths.
13. Validate API authentication, security headers, request validation and error contracts.
14. Validate dashboard behavior on a clean installation.

### P2 — Delivery acceptance

15. Run the complete automated test suite and CI checks on the final v5 baseline.
16. Perform installation/reproducibility validation on a clean Windows environment.
17. Perform application/API/dashboard smoke and end-to-end acceptance.
18. Complete v5 operator, researcher and deployment documentation.
19. Create a final release/demo scenario and acceptance record.
20. Tag the final v5 release only after all P0/P1/P2 acceptance gates pass.

## 6. Research integrity boundary

The repository explicitly distinguishes deterministic demo fixtures from real benchmark evidence. Demo/smoke outputs must not be presented as real SWaT, BATADAL or TON-IoT benchmark performance.

The TON-IoT five-seed benchmark currently integrated into the dashboard is documented as a defined benchmark artifact and includes the limitation that the network CSV lacks a native wall-clock timestamp; its event-order semantics must remain clearly labeled as such.

Actual benchmark files remain deployment/research inputs and must not be committed to source control where dataset terms prohibit redistribution.

## 7. Locked v5 acceptance model

A v5 release is **not accepted** merely because the dashboard loads or `/ready` returns `ready`.

Release acceptance requires all of the following:

```text
Dataset available
  ↓
Dataset validated
  ↓
Preprocessing succeeds
  ↓
Detection succeeds
  ↓
Evaluation succeeds
  ↓
Episode/correlation succeeds
  ↓
Context/ATT&CK succeeds or explicitly reports unresolved mapping
  ↓
Attribution succeeds with valid uncertainty semantics
  ↓
XAI succeeds with usable evidence
  ↓
Risk succeeds
  ↓
CTI/provenance succeeds
  ↓
Dashboard renders the result
  ↓
Clean-installation workflow succeeds
```

## 8. Scope freeze

For the remainder of the v5 delivery cycle, work is restricted to:

- completing the capabilities listed above;
- correcting defects that block acceptance;
- hardening reliability, security, performance and usability;
- completing documentation and reproducibility;
- adding tests required to prove the locked acceptance criteria.

**No new product domain, unrelated feature family, or cosmetic redesign is part of the v5 scope unless it is required to satisfy an existing acceptance criterion.**

## 9. Day 1 exit condition

Day 1 is considered complete when this document is committed to `main` and used as the authoritative v5 execution checklist. Subsequent work should reference these numbered gaps rather than creating a second competing scope.
