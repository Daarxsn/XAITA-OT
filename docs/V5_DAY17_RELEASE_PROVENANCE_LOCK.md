# XAITA-OT V5 — Day 17 Release Provenance Lock

**Status: IMPLEMENTED / ACCEPTANCE IN PROGRESS**

## Scope

Day 17 establishes reproducible release-artifact provenance for the V5 handover. The gate inventories the generated wheel and source distribution, records SHA-256 digests, captures the source commit/ref and runtime version, and preserves the integrity boundary alongside the existing release manifest.

## Delivered

- Deterministic release provenance generator: `scripts/v5_release_provenance.py`.
- SHA-256 digest for every generated wheel and source distribution.
- Release-version consistency check.
- Source commit/ref capture from GitHub Actions when available.
- Release-manifest digest capture.
- Versioned provenance schema: `XAITA-OT-V5.10-RELEASE-PROVENANCE-1.0`.
- Provenance artifact uploaded by the V5 Release Candidate workflow.
- Regression coverage for provenance tooling.
- Explicit boundary: provenance is integrity/build evidence; it is not a cryptographic signature, third-party attestation, penetration test, or production OT acceptance.

## Acceptance criteria

1. Release provenance gate passes.
2. Python 3.11 CI passes.
3. Python 3.12 CI passes.
4. V5 Preflight passes.
5. V5 Operational Check passes.
6. V5 Release Candidate passes and uploads provenance.
7. V5 Clean Install passes.
8. V5 Security Posture passes.
9. Final Day 17 lock evidence is recorded on `main`.

Day 17 is locked only after all required acceptance gates pass on the final implementation commit.
