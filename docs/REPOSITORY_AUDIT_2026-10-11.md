# Repository Audit — 2026-10-11

## Audit baseline

Audited the public `main` snapshot `8ac654cc2267323c49ceb2113b4ef277d39b438b`. Corrections and regression tests are on the separate `audit/repository-hardening-20261011-1549` branch and pull request #25.

## Confirmed fixes in the audit branch

- Parse SWaT and TON-IoT date/time pairs using day-first semantics; combine TON-IoT date/time fields before generic CSV sorting; align the common loader with the validator; require a real timestamp source; and reject duplicate/out-of-order timestamps.
- Refuse to manufacture an all-benign label vector when no label column exists. Explicit missing/unlabeled/negative sentinel values fail closed instead of being silently converted to attacks or normal rows.
- Correct the SWaT unsupervised anomaly-deviation row/feature index; cast Boolean telemetry to `float64`; calculate deviation explanations from the imputed numeric matrix; reject output folders nested in the input root; validate `top_n`; and record empty CSVs as review items.
- Enforce archive download limits while streaming, reject duplicate ZIP extraction destinations, and recognize dotted SWaT A8 archive directory names.
- Exclude symlinked files from lifecycle backups, correctly handle an archive created at backup root, normalize archive paths, and reject duplicate normalized restore paths (including case-only collisions).
- Validate model dimensions, dropout, and learning rate at configuration load time; validate configured ATT&CK reference-profile IDs and reject duplicates/invalid IDs.
- Validate API event timestamps as timezone-aware and feature values as finite; bound request bodies even without `Content-Length`; and improve runtime project-root discovery.
- Reject ambiguous benchmark directories containing multiple CSVs instead of silently selecting one partial file; retain canonical TON-IoT network CSV preference.
- Align MAS with the paper's MITRE ATT&CK Alignment Score (Jaccard similarity between observed techniques and a hypothesis-specific reference technique profile); omit MAS from fusion when no reference profile is configured.
- Align ECS with the episode's measured correlation strength and migrate legacy EC config to ECS rather than double-counting one signal.
- Bind deterministic source-code SHA-256 into real-experiment fingerprints and use strict canonical JSON serialization that rejects NaN/unsupported values.
- Deduplicate repeated STIX attack-pattern objects, reject naive CTI timestamps and invalid ATT&CK IDs, emit canonical MITRE URLs, return domain-specific errors for malformed provenance, and reject empty correlation-weight mappings.
- Package artifacts in Docker; escape API-generated strings before dynamic HTML insertion; and fix incident search to consider all table rows.
- Add regression coverage for the above defects.
- Make the dashboard's research-prototype/demo-data boundary persistent and visible; fix dataset preflight UI precedence so a failed archive cannot be reported READY just because a mounted path exists, and safely render archives with missing hashes.

## Findings that remain acceptance items

1. **Experiment deadline is process-enforced.** Detector fitting now runs in an isolated Python worker. If the deadline expires, the worker process tree is terminated and the direct child is reaped before the API marks the job `timed_out` and returns HTTP 504. Dataset preparation/preflight still runs synchronously before this detector-execution deadline begins.
2. **Readiness is not dataset validation.** `/ready` reports CSV presence. Schema, label, and temporal integrity must be interpreted from preflight validation—not file existence alone.
3. **Some dashboard content is illustrative.** The detection monitor labels its synthetic stream as demo telemetry, but other static incident and chart content is not a live plant feed. It must be backed by actual API telemetry before claiming live monitoring.
4. **SWaT A8 supervised metrics remain blocked by labels.** The available A8 archive has no authoritative ground-truth attack labels. Unsupervised flagged-row proportions are not attack rates and cannot establish precision, recall, F1, or AUROC against true attacks.
5. **MAS profiles require explicit configuration.** The default config leaves `attack_technique_profiles` empty because no defensible hypothesis-specific technique sets are bundled. MAS is explicitly unavailable and omitted from fusion until reference profiles are configured; this avoids inventing ATT&CK alignment ground truth.
6. **Deployment acceptance is environment-specific.** CI cannot prove every private archive, Windows environment, reverse proxy, production auth setting, or customer OT deployment. Test on the intended deployment environment before release.

## Follow-up after timeout and dashboard hardening

- The dashboard displays a persistent warning that incident/asset/monitoring cards are illustrative, and explicitly identifies which status areas are API-backed.
- Dataset readiness display now prioritizes a discovered archive's preflight result; a failed archive can no longer be masked by a present mounted directory, and absent archive hashes no longer break the display.

- A focused process-timeout regression test verifies that a stalled child is terminated within a bounded interval.
- API regression coverage verifies that timeout results become terminal `timed_out` jobs and return HTTP 504.
- The timeout applies to detector execution after dataset preparation and validation; synchronous preparation is still outside that execution deadline and remains a future acceptance item for deployments with hostile or unusually large local archives.

## Verification boundary

A passing test proves only its asserted behavior. CI on PR #25 is the acceptance gate; do not mark the repository release-ready until these checks pass and the remaining findings are fixed or explicitly accepted with documented limits.


## Paper-result integrity corrections

The paper-table generator now refuses to substitute metrics: binary F1 is not Macro-F1; BTAE correlation strength is not correlation F1; presence of provenance IDs is not traceability proof; detector F1 is not attribution F1; and WEF/ACFM scores built from proxy channels are not paper-grade actor-attribution calibration. These unsupported table cells are emitted as `NA`, and the manifest reports `paper_ready: false` unless certified upstream artifacts explicitly declare the required semantics.
