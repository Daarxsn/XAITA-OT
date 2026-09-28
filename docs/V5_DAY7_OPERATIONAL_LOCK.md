# XAITA-OT V5 — Day 7 Operational Lock

**Status: COMPLETE / LOCKED**

Day 7 hardens the V5 analyst-facing operational contract without changing the established research semantics.

## Delivered

- Explicit V5 capability discovery endpoint: `/v2/capabilities`.
- Operational summary endpoint: `/v2/ops/summary`.
- Readiness now reports dashboard and per-dataset readiness instead of only the dashboard flag.
- Supported detector identifiers are explicit and validated before an experiment starts.
- Dataset readiness remains visible for SWaT, BATADAL and TON-IoT.
- Existing API authentication, RBAC, rate limiting, request IDs and security headers remain enforced.
- Analyst execution remains separate from viewer access.
- API tests cover capability discovery, operational summary, readiness, and detector validation.

## Operational contract

### Datasets

- SWaT
- BATADAL
- TON-IoT

### Detectors

- Random Forest (`random_forest`)
- CNN (`cnn`)
- LSTM (`lstm`)
- CNN-LSTM (`cnn_lstm`)

### Attribution configurations

The API exposes the six existing research configurations through the experiment contract: DC, DC+BSS, DC+BSS+ECS, DC+BSS+ECS+MAS, WEF and ACFM.

## Access model

- `viewer`: read-only operational and research status.
- `analyst`: viewer access plus experiment/analyze execution.
- `admin`: full analyst access under the existing role hierarchy.

Authentication can be enabled through the existing deployment environment controls; staging/production require authentication by default.

## Safety boundary

XAITA-OT remains an analyst-support security analytics system. Day 7 does not add autonomous PLC, RTU or SCADA control actions.

## Acceptance evidence

The Day 7 test suite covers:

- health/security headers
- dashboard serving and missing-dashboard handling
- readiness and all-dataset readiness
- authentication and RBAC
- capability contract
- operational summary
- event limits
- unknown dataset rejection
- unknown detector rejection

## Lock rule

Day 7 is considered locked after the GitHub CI matrix passes on Python 3.11 and 3.12 and the V5 operational acceptance check is green. Any later change to the Day 7 contract is Day 8+ work and must not be silently folded into this lock.
