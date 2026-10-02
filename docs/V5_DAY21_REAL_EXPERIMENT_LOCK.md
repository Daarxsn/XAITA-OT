# XAITA-OT V5 — Day 21 Reproducible Real-Experiment Lock

**Status:** IMPLEMENTED / ACCEPTANCE PENDING

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
6. Final GitHub Actions acceptance suite is green on the final implementation commit. — **PENDING**

## Verification boundary

Day 21 establishes the reproducible execution mechanism. It does not claim that any detector has achieved benchmark performance, statistical significance or cross-environment generalization. Real-data performance claims require execution against the authorized benchmark files and archival of the resulting envelopes.

It also does not constitute production OT certification, independent security testing or customer deployment acceptance.

**Day 21 implementation status: COMPLETE.**  
**Day 21 lock status: PENDING CI ACCEPTANCE.**
