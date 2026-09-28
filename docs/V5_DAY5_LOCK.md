# XAITA-OT V5 — Day 5 Deployment Readiness Lock

## Scope

Day 5 closes the deployment-readiness layer on top of the locked Days 1–4 API, dataset, detector and security foundations.

## Locked deliverables

- Read-only deployment preflight covering supported Python, package import, dashboard/config assets and artifact write access.
- Production preflight controls for authentication, HTTPS enforcement, allowed hosts and CORS wildcard rejection.
- Optional real-dataset preflight for SWaT, BATADAL and TON-IoT.
- Automated preflight tests in the repository test suite.
- A machine-readable preflight output schema: `XAITA-OT-V5-PREFLIGHT-1.0`.
- Deployment guidance that keeps benchmark data outside the public Git repository and supports mounted/private runtime data.

## Operational contract

Run:

```text
python scripts/v5_preflight.py
```

For an environment where all three real benchmark datasets must be present:

```text
python scripts/v5_preflight.py --require-datasets
```

For CI/automation:

```text
python scripts/v5_preflight.py --json
```

A production or staging environment must provide API credentials, enable HTTPS redirection, use explicit allowed hosts, and avoid a wildcard CORS policy. The preflight intentionally does not print secrets.

## Data boundary

Raw benchmark files remain deployment/runtime data rather than source-controlled application assets. The existing runtime preparation path supports a mounted private dataset or a private archive with optional SHA-256 verification.

## Acceptance

Day 5 is locked when the repository CI suite passes and the deployment preflight itself reports no errors for the intended environment. A passing development preflight does not claim that an external customer environment has been independently security-tested, load-tested, or approved against its OT safety policy.
