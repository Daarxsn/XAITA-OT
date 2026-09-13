# XAITA-OT V5 Roadmap

## Purpose

V5 is the next engineering phase after the V4.5 release-readiness baseline. It must extend XAITA-OT without weakening the V1–V4 research, safety, provenance, or deployment boundaries.

## V5 engineering principles

- Preserve the canonical pipeline: Observation → Detection → Episode → Context → Attribution → Explanation → Risk → CTI.
- Preserve the separation between Detection Confidence (DC) and Attribution Confidence (AC).
- Preserve evidence IDs, provenance links, uncertainty, and analyst-support-only deployment boundaries.
- Prefer backward-compatible, tested changes over broad rewrites.
- Every feature must have unit, integration, or acceptance coverage appropriate to its risk.
- No benchmark claim may be made without a reproducible run on the specified real dataset.

## Delivery sequence

### V5.1 — Baseline hardening and developer contract

- Audit the V4.5 branch baseline and identify incomplete, fragile, or undocumented behavior.
- Freeze the public Python/API/CLI contracts that V5 will preserve.
- Add a V5 version/feature capability contract.
- Add regression coverage for the existing CLI, API, provenance, confidence separation, and safety boundaries.
- Confirm clean-install and supported Python-version CI behavior.

**Exit gate:** V5.1 changes are documented, backward-compatible, covered by tests, and all CI checks pass.

### V5.2 — Evidence and provenance quality

- Strengthen evidence lineage and provenance validation.
- Validate supporting, conflicting, and unresolved evidence handling.
- Add deterministic serialization and validation checks where needed.
- Improve analyst-facing traceability without exposing secrets or restricted data.

**Exit gate:** provenance and evidence invariants are tested end to end.

### V5.3 — Attribution and explanation quality

- Improve attribution evaluation and explanation consistency.
- Preserve DC ≠ AC semantics in every output surface.
- Add regression tests for competing hypotheses, uncertainty, and explanation fidelity.
- Keep model and behavioral explanations reproducible.

**Exit gate:** attribution/explanation behavior is reproducible and acceptance-tested.

### V5.4 — Operational robustness

- Review API error handling, input validation, observability, and resource limits.
- Add safe failure behavior and operational diagnostics.
- Review container/runtime configuration and least-privilege assumptions.
- Add performance and load checks where supported by the existing architecture.

**Exit gate:** operational failure modes are documented and tested.

### V5.5 — V5 release readiness

- Run the complete test, smoke, install, security, and documentation gates.
- Update the README and release notes with verified capabilities only.
- Produce reproducible artifacts and an explicit verification boundary.
- Open the V5 release pull request only after all gates pass.

**Exit gate:** V5 is release-ready and its claims are backed by executable evidence.

## Immediate next task

Inspect the V4.5 implementation and tests, then create the V5.1 baseline-hardening issue list before making behavior-changing changes.
