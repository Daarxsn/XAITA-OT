# XAITA-OT V5 — Day 8 Deployment Integration Lock

## Scope

Day 8 closes the gap between source-level CI acceptance and a disposable running-service acceptance test. The goal is to prove that the packaged API can start in a staging-like environment, serve the dashboard, discover all three dataset mounts, expose the V5 capability/operations contracts, and enforce the authentication boundary.

## Locked deliverables

- Disposable end-to-end deployment smoke: `scripts/v5_e2e_smoke.py`.
- Synthetic temporary dataset mounts for SWaT, BATADAL and TON-IoT; no benchmark files are modified.
- Staging-like authentication with viewer, analyst and admin roles.
- Health and readiness verification.
- Dashboard delivery verification.
- Dataset readiness verification for all three supported datasets.
- V5 system and capability discovery verification.
- V5 operational summary verification.
- Unauthenticated analyst endpoint rejection.
- Invalid API credential rejection.
- Automatic process cleanup after the smoke test.
- GitHub CI gate runs the disposable deployment smoke after the existing test and V3 acceptance suite.

## Safety boundary

The Day 8 smoke test does not execute real detector training, connect to PLC/RTU/SCADA systems, modify benchmark data, or issue OT control actions. It validates service integration using disposable synthetic runtime data.

## Acceptance command

Run from a clean checkout:

```text
python scripts/v5_e2e_smoke.py
```

Expected final line:

```text
E2E smoke: PASS
```

## Lock criteria

Day 8 is locked only when:

1. Python 3.11 CI passes.
2. Python 3.12 CI passes.
3. Dependency audit passes.
4. Existing V5 preflight passes.
5. Existing V5 operational acceptance passes.
6. The disposable end-to-end deployment smoke passes.
7. The Day 8 lock document is present on `main`.

A passing disposable smoke is deployment-integration evidence only. It does not claim customer-network acceptance, OT safety certification, penetration-test completion, load-test capacity, or regulatory certification.
