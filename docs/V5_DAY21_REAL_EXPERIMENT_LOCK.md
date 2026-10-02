# XAITA-OT V5 — Day 21 Reproducible Real-Experiment Lock

**Status:** COMPLETE / LOCKED

## Scope

Day 21 adds the controlled real-benchmark experiment execution layer on top of the Day 20 validation gate.

## Delivered

- Reproducible real-experiment runner in `src/xaita_ot/pipeline/real_experiments.py`.
- Validation-before-execution gate: a dataset that fails Day 20 validation cannot enter the real experiment path.
- Auditable result envelope containing:
  - dataset validation record
  - dataset SHA-256
  - experiment ID
  - dataset
  - detector
  - seed
  - split protocol
  - configuration
  - configuration SHA-256
  - deterministic reproducibility fingerprint
  - package version
- CLI command:
  `xaita real-experiment`
- Contract extension and documentation.
- Regression coverage for deterministic fingerprints, audit envelopes, blocked invalid input and the accepted execution path.
- README usage documentation.

## Acceptance criteria

1. Real experiment execution is gated by dataset validation. — **PASS**
2. Result envelopes retain dataset, detector, seed and split identity. — **PASS**
3. File and configuration identity are hashable and reproducible. — **PASS**
4. Invalid benchmark input cannot silently proceed to model execution. — **PASS**
5. CLI and developer contract are documented. — **PASS**
6. Final GitHub Actions acceptance suite is green on the final implementation commit. — **PASS**

## Verification boundary

Day 21 establishes the reproducible execution mechanism. It does not claim that any detector has achieved benchmark performance, statistical significance or cross-environment generalization. Real-data performance claims require execution against the authorized benchmark files and archival of the resulting envelopes.

It also does not constitute production OT certification, independent security testing or customer deployment acceptance.

## Final acceptance evidence

Final accepted commit: `cbf4d873cd348dfee631b31216658413de7ee423`

GitHub Actions on the final implementation commit:
- XAITA-OT CI — **success**
- V5 Preflight — **success**
- V5 Operational Check — **success**
- V5 Release Candidate — **success**
- V5 Security Posture — **success**
- V5 Clean Install — **success**
- V5 Release Provenance — **success**

**Day 21 implementation status: COMPLETE.**  
**Day 21 status: LOCKED.**
