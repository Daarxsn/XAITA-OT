# XAITA-OT V5 — Day 14 Release Candidate & Artifact Lock

**Status: IMPLEMENTED / ACCEPTANCE IN PROGRESS**

## Scope

Day 14 establishes a reproducible V5 release-candidate artifact gate. The gate builds the package from source, verifies wheel and source-distribution metadata, records artifact hashes and sizes, and publishes CI artifacts for both supported Python versions.

## Delivered

- Dedicated V5 release-candidate GitHub Actions workflow.
- Python 3.11 and 3.12 release-candidate matrix.
- Wheel and source-distribution build using the repository package metadata.
- Release artifact integrity and metadata verification through scripts/v5_release_artifact_check.py.
- Release-manifest regression execution.
- CI artifact upload for the generated wheel, source distribution and release manifest.
- Explicit verification boundary retained: artifact integrity is not production OT safety certification, independent penetration testing, or customer-specific deployment acceptance.

## Acceptance criteria

1. Python 3.11 release-candidate build passes.
2. Python 3.12 release-candidate build passes.
3. Wheel metadata matches package xaita-ot and version 0.5.1.
4. Source distribution root/version metadata is valid.
5. Artifact SHA-256 manifest is generated successfully.
6. Release-manifest regression passes.
7. Existing XAITA-OT CI, V5 Preflight and V5 Operational Check remain green.
8. Final Day 14 lock evidence is recorded on main.

Day 14 will be locked only after all required acceptance gates pass on the final implementation commit.
