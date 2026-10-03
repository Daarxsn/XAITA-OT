# XAITA-OT V5 — Security Evidence Contract

## Purpose

Day 32 establishes executable security evidence gates for the repository. The gates cover Python static analysis, installed dependency vulnerability auditing, and filesystem/container vulnerability scanning.

## Automated evidence

| Control | Tool | Gate |
|---|---|---|
| Python SAST | Bandit | High-confidence findings fail the workflow according to the configured Bandit policy |
| Python dependency vulnerabilities | pip-audit | Vulnerability findings fail the workflow |
| Repository/filesystem vulnerabilities | Trivy | HIGH/CRITICAL findings fail the workflow |
| Built container vulnerabilities | Trivy | HIGH/CRITICAL findings fail the workflow; unfixed findings are reported but do not fail this image gate |

## Evidence retention

Security scan JSON reports are written under `artifacts/security/` in the workflow workspace. The workflow is the executable acceptance gate; a green run means the scanned revision passed the configured checks at that point in time.

## Review boundary

These controls are security evidence, not security certification. A green scan does not establish absence of unknown vulnerabilities, penetration-test coverage, supply-chain compromise, customer acceptance, or production OT safety.

The repository remains analyst-support only and does not authorize autonomous PLC/RTU/SCADA control.

## Maintenance

Security tooling versions/actions must be reviewed as part of dependency and CI maintenance. Findings that are suppressed or ignored must be documented with scope and rationale rather than silently removed.
