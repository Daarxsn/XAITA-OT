# XAITA-OT V5 — Day 15 Clean Install & Handover Lock

**Status: IMPLEMENTED / ACCEPTANCE IN PROGRESS**

## Scope

Day 15 establishes an isolated clean-install gate for the V5 handover. A release wheel is built in CI, installed into a fresh virtual environment, and exercised through package import and the public CLI entry point.

## Delivered

- Deterministic isolated clean-install smoke: scripts/v5_clean_install_smoke.py.
- Python 3.11 and 3.12 clean-install matrix.
- Fresh virtual-environment creation per test run.
- Release wheel installation from the generated artifact.
- Package import verification.
- Public `xaita --help` entry-point verification.
- Dedicated V5 Clean Install GitHub Actions workflow.
- Regression coverage for the clean-install smoke tooling.
- Explicit boundary: this verifies packaging and handover usability, not production OT deployment, penetration testing, safety certification or customer acceptance.

## Acceptance criteria

1. Python 3.11 clean-install gate passes.
2. Python 3.12 clean-install gate passes.
3. Existing XAITA-OT CI passes.
4. V5 Preflight passes.
5. V5 Operational Check passes.
6. V5 Release Candidate remains green.
7. Clean-install regression passes.
8. Final Day 15 lock evidence is recorded on main.

Day 15 will be locked only after all required acceptance gates pass on the final implementation commit.
