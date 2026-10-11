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

## Findings that remain acceptance items

1. **Execution deadline is not process termination.** The documented lifecycle marks a job `timed_out` only after `run_detection` returns. It does not interrupt a running model fit; hard cancellation would need isolated workers/processes and explicit cancellation tests.
2. **Readiness is not dataset validation.** `/ready` reports CSV presence. Schema, label, and temporal integrity must be interpreted from preflight validation—not file existence alone.
3. **Some dashboard content is illustrative.** The detection monitor labels its synthetic stream as demo telemetry, but other static incident and chart content is not a live plant feed. It must be backed by actual API telemetry before claiming live monitoring.
4. **SWaT A8 supervised metrics remain blocked by labels.** The available A8 archive has no authoritative ground-truth attack labels. Unsupervised flagged-row proportions are not attack rates and cannot establish precision, recall, F1, or AUROC against true attacks.
5. **MAS profiles require explicit configuration.** The default config leaves `attack_technique_profiles` empty because no defensible hypothesis-specific technique sets are bundled. MAS is explicitly unavailable and omitted from fusion until reference profiles are configured; this avoids inventing ATT&CK alignment ground truth.
6. **Deployment acceptance is environment-specific.** CI cannot prove every private archive, Windows environment, reverse proxy, production auth setting, or customer OT deployment. Test on the intended deployment environment before release.

## Verification boundary

A passing test proves only its asserted behavior. CI on PR #25 is the acceptance gate; do not mark the repository release-ready until these checks pass and the remaining findings are fixed or explicitly accepted with documented limits.
