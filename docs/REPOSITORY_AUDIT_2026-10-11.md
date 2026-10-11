# Repository Audit — 2026-10-11

## Audit baseline

Audited main commit `8ac654cc2267323c49ceb2113b4ef277d39b438b`. This branch contains targeted corrections and regression coverage; it is intentionally separate from `main`.

## Correctness and hardening fixes

- Parse SWaT timestamps with day-first semantics, require a real timestamp source for TON-IoT validation, and count explicit missing/unlabeled sentinels as unknown rather than confirmed attacks.
- Correct the SWaT unsupervised anomaly-deviation row/feature index; cast Boolean telemetry to numeric float64; reject output folders nested in the input root; validate `top_n`; report empty CSVs as review items.
- Enforce archive download size caps while streaming; reject duplicate ZIP destinations.
- Exclude symlinked files from lifecycle backups and avoid excluding the entire root when the backup archive is written directly in the project root; normalize archive path separators.
- Fail fast for invalid model dimensions, dropout and learning-rate configuration.
- Resolve the application root for installed/container execution, enforce body limits when `Content-Length` is absent, include published artifacts in the Docker image, escape API-generated HTML, and fix filtering to cover all incident rows.
- Add regression tests for these behaviors.

## Follow-up findings that still need explicit acceptance

1. **Experiment timeout is post-hoc.** `/v2/experiment` measures training duration and only marks a run timed out after `run_detection` returns. It does not stop the computation at the configured deadline. A worker/process-based execution lifecycle needs implementation and dedicated cancellation tests before describing this as an enforced runtime timeout.
2. **Some dashboard monitoring content is demo data.** The hard-coded incident row and monitoring events, and random bar rendering, are not a live stream from a deployed OT environment. They must be visibly classified as illustrative or replaced with API-backed telemetry before claiming live monitoring.
3. **Readiness currently reflects file presence, not benchmark validity.** A directory with at least one CSV can be shown as configured/ready even when those CSVs fail schema, timestamp, or label checks. Use dataset preflight/validation separately and make these statuses explicit.
4. **Dataset selection can be ambiguous.** The API chooses a candidate CSV from a dataset directory; for nested/per-chunk corpora, a deterministic and documented selection policy (or an explicit file path) is needed to prevent an arbitrary subset being treated as the benchmark.
5. **Benchmark evidence remains data-dependent.** SWaT A8 currently lacks authoritative labels in the archive used for unsupervised analysis; that output cannot support supervised precision/recall/AUROC claims. Do not promote anomaly-flagging ratios as attack rates.
6. **Deployment-specific acceptance remains necessary.** The repo's CI workflow passing is valuable but does not prove every private dataset archive, OS, reverse proxy, production auth configuration, or customer OT deployment is valid.

## Verification boundary

A regression test passing proves only the asserted behavior. The repository's CI pipeline is the acceptance gate for these changes. Release readiness must remain conditional until CI on this branch passes and the follow-up findings above are either fixed or explicitly accepted with documented limitations.
