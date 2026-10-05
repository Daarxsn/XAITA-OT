# XAITA-OT V5 — Day 35 Operations Documentation Lock

**Status:** COMPLETE / LOCKED

## Scope

Day 35 closes the V5 P2 **Operations documentation** requirement with a repeatable operator runbook, troubleshooting workflow and independent-user acceptance contract.

## Delivered

- Versioned independent acceptance contract: `XAITA-OT-V5-INDEPENDENT-ACCEPTANCE-1.0`.
- One commandable acceptance workflow combining:
  - required operational-surface verification
  - deployment preflight
  - disposable end-to-end smoke
  - optional live operational probe
- Machine-readable JSON output for acceptance evidence.
- Explicit distinction between repository/disposable acceptance and live deployment acceptance.
- Troubleshooting workflow tied to health, readiness, authentication, security headers, dataset state, system state and request correlation.
- Existing recovery/rollback runbook integrated into the operational workflow.
- Regression coverage for the acceptance contract and its live-validation boundary.

## Independent acceptance workflow

Repository/disposable acceptance:

```powershell
python scripts/v5_user_acceptance.py
```

Machine-readable evidence:

```powershell
python scripts/v5_user_acceptance.py --json
```

Approved live/staging deployment acceptance:

```powershell
python scripts/v5_user_acceptance.py --base-url https://<approved-deployment> --json
```

A live URL is intentionally required before the workflow claims live operational acceptance.

## Troubleshooting order

1. Run `python scripts/v5_preflight.py --json`.
2. Check `/health`.
3. Check `/ready` and dashboard availability.
4. Check `X-Request-ID` correlation.
5. Check security headers.
6. Check authentication/RBAC behavior.
7. Check dataset readiness.
8. Check `/v2/system` and `/v2/ops/summary`.
9. Run the disposable E2E smoke to separate application defects from environment-specific deployment issues.
10. If the issue follows an upgrade, use the Day 34 verified-backup and staged-restore workflow.

## Acceptance criteria

1. Operator runbook has a deterministic starting point. — **PASS**
2. Independent acceptance is executable and machine-readable. — **PASS**
3. Troubleshooting order is explicit. — **PASS**
4. Live deployment acceptance cannot be claimed without an approved deployment URL. — **PASS**
5. Recovery/rollback procedure is linked to the troubleshooting flow. — **PASS**
6. Regression tests cover the acceptance contract. — **PASS**
7. Final repository CI is green on the Day 35 lock commit. — **PENDING FINAL CI**

## Verification boundary

Day 35 provides a repeatable operations handover workflow. It does not claim external uptime, customer acceptance, production OT safety certification, penetration-test completion, RTO/RPO certification, or regulatory compliance. Live acceptance remains environment-specific and requires an approved deployment target.

## OT safety boundary

The acceptance workflow is diagnostic and read-only. It does not issue PLC/RTU/SCADA control commands and does not authorize autonomous OT action.
