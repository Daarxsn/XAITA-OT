# XAITA-OT V5 — Day 20 Real-Dataset Validation Lock

**Status:** IMPLEMENTED / ACCEPTANCE PENDING

## Scope

Day 20 establishes the repository-level validation and reproducibility layer for researcher-supplied SWaT, BATADAL and TON-IoT benchmark files.

## Delivered

- Real CSV validation module: `src/xaita_ot/io/dataset_validation.py`.
- Dataset-aware timestamp and label resolution.
- SWaT `Attack State` handling.
- BATADAL day-first timestamp parsing.
- TON-IoT `date + time` timestamp reconstruction.
- Chunked CSV inspection for large files.
- Missing-value, invalid-timestamp, duplicate-timestamp and ordering checks.
- Label distribution reporting.
- SHA-256 file identity.
- Location-independent deterministic manifest digests.
- Single-dataset CLI: `xaita validate-data`.
- All-dataset local runner: `scripts/v5_validate_local_datasets.py`.
- Regression coverage for validation, CLI behavior and multi-dataset execution.
- README and developer-contract documentation updated.

## Acceptance criteria

1. Dataset-specific timestamp/label rules are implemented and tested. — **PASS**
2. Large CSVs are processed in chunks. — **PASS**
3. Raw benchmark files remain outside source control. — **PASS**
4. File identity and reproducibility metadata are recorded. — **PASS**
5. Validation failures are surfaced as review states rather than silently accepted. — **PASS**
6. Validation CLI and all-dataset runner are documented. — **PASS**
7. Final GitHub Actions acceptance suite is green on the final implementation commit. — **PENDING**

## Verification boundary

Day 20 provides the validation/reproducibility mechanism. A passing file manifest means the supplied files satisfy the implemented ingestion checks; it does not claim detector performance, statistical significance, cross-environment generalization, independent security assessment, production OT certification or customer acceptance.

**Day 20 implementation status: COMPLETE.**  
**Day 20 lock status: PENDING CI ACCEPTANCE.**
