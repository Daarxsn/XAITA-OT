# Repository Audit — 2026-10-11

## Audit baseline

Audited the public `main` snapshot `8ac654cc2267323c49ceb2113b4ef277d39b438b`. Corrections and regression tests are maintained on the separate `audit/repository-hardening-20261011-1549` branch and pull request #25.

## Confirmed fixes in the audit branch

- Parse SWaT and TON-IoT date/time pairs with day-first semantics; require a real timestamp source; and make dataset preflight reject duplicate or out-of-order timestamps that would later be rejected by execution.
- Count missing/unlabeled values as unknown rather than confirmed attacks.
- Correct the SWaT unsupervised anomaly-deviation row/feature index; cast Boolean telemetry to `float64`; reject output folders nested in the input root; validate `top_n`; and record empty CSVs as review items.
- Enforce archive download limits while streaming and reject duplicate ZIP extraction destinations.
- Exclude symlinked files from lifecycle backups and correctly handle an archive created at the backup root; normalize archive paths.
- Validate model dimensions, dropout, and learning rate at configuration load time.
- Add timezone-awareness and finite-value validation for API event inputs, bound chunked request bodies, and improve runtime project-root discovery.
- Reject ambiguous directories containing multiple candidate benchmark CSVs rather than silently benchmarking one partial file. Retain the explicit TON-IoT `train_test_network.csv` preference.
- Fix the Multi-Asset/Protocol consistency score so repeated known asset/protocol values score as more consistent than diverse values; unknown context does not count as reliable consistency.
- Include a deterministic source-code SHA-256 in experiment reproducibility fingerprints so two builds with identical data/config/seeds but different Python source do not silently share the same identity.
- Deduplicate repeated STIX attack-pattern objects, reject naive CTI timestamps, return domain-specific errors for malformed provenance items, and reject an explicitly empty correlation-weight mapping.
- Resolve the application root more reliably, package artifacts in Docker, escape API-generated HTML and make incident search work across all rows.
- Add regression tests covering these bug classes.

## Findings that remain acceptance items

1. **Execution deadline is not process termination.** The documented contract marks a job `timed_out` only after `run_detection` returns; it does not interrupt a running model fit. The README discloses this behavior. If hard cancellation is required operationally, an isolated worker/process model and cancellation tests are still needed.
2. **Readiness is not dataset validation.** `/ready` reports configured CSV presence; benchmark schema, labels and temporal integrity require the dataset preflight endpoint. Keep the UI/API wording explicit so “configured” is not interpreted as “validated.”
3. **Monitoring is illustrative, not live OT data.** The detection monitor labels its synthetic stream as demo telemetry; the separately hard-coded incident content and chart are not a live plant connection. Replace them with real API-backed incidents before claiming live monitoring.
4. **SWaT A8 supervised metrics are still blocked by label provenance.** The currently available A8 archive has no authoritative ground-truth attack labels. Unsupervised anomaly-flagging ratios are not attack rates, and cannot establish precision, recall, F1 or AUROC against actual attacks.
5. **Deployment acceptance remains environment-specific.** The CI suite is essential, but cannot prove every private archive, Windows path, reverse proxy, production authentication setting, or customer OT deployment. Perform the target-environment smoke and security checks before release.

## Verification boundary

A passing regression test proves only the behavior asserted by that test. The pull request CI suite is the acceptance gate for these changes. Do not mark the whole repository release-ready until those checks pass and the follow-up findings above are fixed or explicitly accepted and documented.
