# XAITA-OT V5 — Day 34 Recovery and Lifecycle Operations Lock

**Status:** COMPLETE / LOCKED

## Scope

Day 34 closes the V5 P2 **Recovery and lifecycle operations** requirement with executable repository-local backup, verification, restore-to-staging, retention and upgrade/rollback planning controls.

## Delivered

- Versioned lifecycle backup manifest: `XAITA-OT-LIFECYCLE-BACKUP-1.0`.
- SHA-256 inventory for backed-up files.
- Automatic exclusion of raw research datasets under `data/raw`.
- Backup archive creation as a compressed tarball.
- Fail-closed backup verification.
- Restore only after successful verification.
- Restore destination must be empty; the tool never overwrites a live deployment root.
- Retention pruning that keeps the newest configured number of backups.
- Versioned upgrade/rollback plan: `XAITA-OT-LIFECYCLE-PLAN-1.0`.
- Explicit pre-upgrade backup/verification sequence.
- Explicit post-upgrade health/smoke validation sequence.
- Explicit rollback sequence.
- Default rollback revision bound to the known current revision.
- CLI commands:
  - `xaita backup`
  - `xaita backup-verify`
  - `xaita backup-restore`
  - `xaita backup-prune`
  - `xaita lifecycle-plan`
- Regression coverage for checksums, raw-data exclusion, restore safety, retention, lifecycle planning and CLI behavior.
- Operator recovery documentation.

## Recovery workflow

1. Create a backup before an upgrade.
2. Verify the backup checksum inventory.
3. Record the current revision.
4. Deploy the target revision.
5. Run health and smoke checks.
6. If the release is unacceptable, stop the new revision and restore the verified backup into staging.
7. Redeploy the previous revision and repeat health/smoke validation.
8. Prune old backups only after the retained set has been verified.

## Acceptance criteria

1. Backup manifest is versioned and checksum-bound. — **PASS**
2. Raw research datasets are excluded by default. — **PASS**
3. Backup verification fails closed on missing/corrupt members. — **PASS**
4. Restore requires a verified backup and empty staging destination. — **PASS**
5. Retention policy is executable and bounded. — **PASS**
6. Upgrade and rollback sequence is explicitly represented. — **PASS**
7. CLI and regression tests cover the lifecycle controls. — **PASS**
8. Final repository CI is green on the Day 34 lock commit. — **PASS**

## Verification boundary

These controls provide repository-local recovery evidence. They do not provide distributed storage durability, off-site disaster recovery, database-specific point-in-time recovery, infrastructure orchestration, guaranteed service continuity, or customer-specific RTO/RPO certification. Production operators remain responsible for secure backup storage, access controls, independent backup copies, environment-specific validation and approved change-management procedures.

## OT safety boundary

Backup, restore and rollback tooling does not issue PLC/RTU/SCADA commands and does not authorize autonomous OT actions. Restores are staged rather than applied directly to a live control environment.
