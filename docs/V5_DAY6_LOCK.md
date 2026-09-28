# XAITA-OT V5 — Day 6 Operational Acceptance Lock

## Scope

Day 6 adds the operational acceptance layer on top of the locked V5 deployment-readiness foundation. It validates the service from the outside through a dependency-light probe rather than treating source-level tests as proof that a running deployment is reachable and correctly exposing its safety/security boundary.

## Locked deliverables

- Read-only operational probe for `/health`, `/ready`, dashboard delivery, dataset status and system status.
- Request-correlation verification through `X-Request-ID`.
- Baseline HTTP security-header verification.
- Authentication-boundary verification for the analyst endpoint.
- Machine-readable operational schema: `XAITA-OT-V5-OPS-1.0`.
- Automated unit tests for successful and failing operational conditions.
- Dedicated GitHub Actions operational acceptance gate.
- No credential values are printed by the operational probe.

## Operational contract

Run locally against a running service:

```text
python scripts/v5_operational_check.py
```

Machine-readable output:

```text
python scripts/v5_operational_check.py --json
```

Against another deployment:

```text
python scripts/v5_operational_check.py --base-url https://host.example
```

For staging/production authentication enforcement:

```text
python scripts/v5_operational_check.py --base-url https://host.example --require-auth
```

If a credential is required, supply it through `XAITA_API_KEY` or `--api-key`; the value is used only for the request and is never included in output.

## Acceptance boundary

Day 6 confirms the application contract and observable security controls. It does not claim live-OT safety certification, penetration-test completion, customer-network acceptance, load-test capacity, or regulatory certification. Those require environment-specific evidence.

## Lock criteria

The repository gate must pass the operational-check tests and the existing V5 deployment preflight. A running customer deployment should additionally execute the probe against its actual base URL before handover.
