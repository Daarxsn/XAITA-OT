# Operations Guide

## Passive deployment principle

Run XAITA-OT on mirrored telemetry, SIEM/OT monitoring exports, historian/process data, or other approved read-only feeds. Do not connect the module to control-plane write paths for autonomous response.

## Recovery, backup and rollback

XAITA-OT provides repository-local lifecycle helpers for creating checksum-bound backups, verifying them, restoring them into an empty staging directory, pruning old backups, and generating an explicit upgrade/rollback plan.

Create a backup before a change:

```powershell
xaita backup --root . --out artifacts/backups/xaita-backup-<revision>.tar.gz
```

Verify it before relying on it:

```powershell
xaita backup-verify --backup artifacts/backups/xaita-backup-<revision>.tar.gz
```

Restore only into an empty staging directory:

```powershell
xaita backup-restore --backup artifacts/backups/xaita-backup-<revision>.tar.gz --staging artifacts/recovery/staging
```

Generate an explicit upgrade/rollback plan:

```powershell
xaita lifecycle-plan --current-revision <current> --target-revision <target> --backup artifacts/backups/xaita-backup-<revision>.tar.gz
```

Retain only the newest backups after verification:

```powershell
xaita backup-prune --directory artifacts/backups --keep 5
```

Raw research datasets under `data/raw` are excluded by default. Backup verification is checksum-bound and restore fails closed if verification fails. Restore is deliberately staging-only; deployment operators must review and promote restored state through their approved change-management process.

For production use, store backups independently from the application host, apply access controls, maintain multiple approved copies, and validate environment-specific recovery procedures and RTO/RPO requirements. These repository-local helpers do not constitute disaster-recovery certification.

## Independent-user acceptance

Run the repository and disposable acceptance workflow before handover:

```powershell
python scripts/v5_user_acceptance.py
```

For machine-readable evidence:

```powershell
python scripts/v5_user_acceptance.py --json
```

For an approved staging/production deployment, supply the approved deployment URL:

```powershell
python scripts/v5_user_acceptance.py --base-url https://<approved-deployment> --json
```

The workflow intentionally does not claim live acceptance when no deployment URL is supplied. The live probe checks health, readiness, dashboard response, request correlation, baseline security headers, dataset status, system status and authentication boundaries.

### Troubleshooting order

1. Run the preflight and inspect all error checks.
2. Verify `/health`.
3. Verify `/ready` and dashboard availability.
4. Verify request correlation via `X-Request-ID`.
5. Verify baseline security headers.
6. Verify authentication/RBAC behavior.
7. Verify dataset readiness and `/v2/system`.
8. Run the disposable E2E smoke to isolate application behavior from deployment-specific behavior.
9. For post-upgrade regressions, use the verified Day 34 backup/restore and rollback workflow.

## Production checklist

- [ ] Dataset and telemetry ownership/permissions approved
- [ ] Network segmentation and firewall policy reviewed
- [ ] Secrets stored outside source code
- [ ] API authentication/RBAC enabled by deployment platform
- [ ] TLS terminated at approved gateway
- [ ] Audit logging enabled and retained per policy
- [ ] Model/version provenance recorded
- [ ] ATT&CK mapping release pinned and reviewed
- [ ] Thresholds validated on environment-specific validation data
- [ ] Load/latency tested at expected event rates
- [ ] Human validation workflow established
- [ ] Incident-response and rollback procedures tested
- [ ] Safety/security review completed before production use
