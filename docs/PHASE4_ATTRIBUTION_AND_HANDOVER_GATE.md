# XAITA-OT Phase 4 Attribution Evaluation and Pre-Handover Gate

**Status: IN PROGRESS — acceptance must be supported by final-commit evidence.**

This checklist combines the agreed Phase 4 attribution evaluation with the separate complete pre-handover gate. It does not replace the V5.1 developer contract, V3.1 evidence freeze, or V4 enterprise-hardening roadmap.

Implementation entry point: `scripts/run_phase4_attribution.py` backed by `xaita_ot.pipeline.attribution_evaluation`. The existing `scripts/run_v3_phase4.py` is the separate V3.4 ablation study; it is not a substitute for the C1-C6 matrix. CI runs C1-C6 against synthetic fixtures to test execution and artifact structure only. The current C1-C6 runner uses one shared Random Forest detection-score baseline across all six configurations; the separate four-detector suite is still required for the broader detector acceptance gate. That smoke run is not real benchmark evidence.

## 1. Phase 4 attribution evaluation

Evaluate the same eligible cases and ground-truth protocol across these configurations:

| ID | Configuration | Required comparison |
|---|---|---|
| C1 | Detection only (DC) | Detection-only reference |
| C2 | DC + BSS | Incremental effect of BSS |
| C3 | DC + BSS + ECS | Incremental effect of ECS |
| C4 | DC + BSS + ECS + MAS | Incremental effect of MAS |
| C5 | WEF | Weighted Evidence Fusion baseline |
| C6 | ACFM | ACFM comparison against the same eligible cases |

Report, where ground truth and protocol support the metric:

- Attribution precision, recall and F1, with denominators and zero-division policy.
- Hypothesis ranking quality (top-1 and top-k, where labels support it).
- Detection confidence (DC) separately from attribution confidence (AC).
- Calibration/reliability and uncertainty/interval width where the method returns a calibrated probability or interval.
- Per-dataset and per-seed results, sample counts, confidence intervals where appropriate, runtime and resource usage.
- Failure, abstention and unknown-ground-truth counts. Never turn unavailable metrics into zero or hide them as unexplained NA.

**Fairness rule:** configurations must use the same eligible examples, labels, split boundaries and scoring definitions. Any configuration-specific exclusions must be reported. DC and AC must remain semantically distinct. Unlabeled SWaT analysis is exploratory and cannot supply attack-ground-truth attribution scores.

## 2. Data integrity and research validity

- [ ] Dataset identity, source/licence notes, file hashes, schema, row counts and label semantics are recorded.
- [ ] Timestamps are parsed consistently; invalid, duplicate, out-of-order and placeholder timestamps are quantified.
- [ ] Missing labels are a hard evaluation blocker; missing feature cells are separately counted and preprocessing is documented.
- [ ] Splits are chronological/episode-aware where appropriate and avoid leakage across adjacent windows or attack episodes.
- [ ] Train-fitted preprocessing does not learn from validation/test data.
- [ ] Real benchmark results are explicitly distinguished from synthetic fixtures and unlabeled anomaly flags.
- [ ] All four detector configurations (Random Forest, CNN, LSTM and CNN-LSTM) have run records, failures, metrics and reproducibility metadata where eligible.
- [ ] Each reported metric is reproducible from the saved artifact; unsupported metrics are labelled not_evaluated with a reason.

## 3. Engineering QA and security

- [ ] Clean checkout and supported Python versions install from documented instructions.
- [ ] Unit, integration, regression, API, failure-path and contract tests pass on the final commit.
- [ ] CLI commands, exit codes, validation failures and error messages are covered.
- [ ] API authentication/RBAC negative tests prove viewers cannot execute analyst operations and unauthenticated production requests are rejected.
- [ ] API responses do not expose secrets, raw credentials or private local filesystem paths.
- [ ] Request limits, rate limits, experiment concurrency, timeout/failure states and job retention are exercised. The current thread-based timeout returns the API response at the deadline but cannot kill a hung worker; use process isolation if hard termination is required.
- [ ] Dependency/security scans run; findings are fixed or documented with explicit risk acceptance.
- [ ] Evidence IDs, provenance links, DC/AC separation and uncertainty survive the end-to-end analytical pipeline.
- [ ] No component sends PLC/RTU/SCADA control commands or autonomously performs safety-critical OT actions.

## 4. Dashboard and operator experience

- [ ] Dataset file presence is not presented as benchmark validation success.
- [ ] Demo/simulated content is visibly identified; telemetry not returned by an API is never presented as live.
- [ ] Loading, empty, error, stale-data and permission-denied states are understandable and recoverable.
- [ ] Dashboard values come from the API or are explicitly labelled as examples.
- [ ] Navigation, filters, copy/export, API-key session handling and refresh controls work.
- [ ] Responsive layouts, keyboard navigation, focus states, contrast, labels and screen-reader status announcements are checked.
- [ ] No dark-on-dark or low-contrast states occur in any supported theme.

## 5. Deployment and handover

- [ ] Docker/container build succeeds from a clean environment with documented configuration.
- [ ] Health, readiness, dashboard, authenticated API and end-to-end smoke checks pass.
- [ ] Dataset mounts/archive setup, resource bounds, logs, backup, recovery, upgrade, rollback and retention are documented.
- [ ] API routes, schemas, roles, environment variables and safe deployment defaults are synchronized with the code.
- [ ] Known limitations, data licensing, benchmark eligibility, scientific caveats and OT safety boundaries are explicit.
- [ ] Final commit has green CI; artifacts and test logs identify that exact commit.
- [ ] Repository is clean and versioned; release tag is created only after evidence is accepted.
- [ ] V3.1 research baseline is frozen before beginning V4 enterprise hardening, as agreed.

## 6. Closure record

For each checklist item, record one of: PASS, FAIL, BLOCKED, NOT RUN, or NOT APPLICABLE. Include evidence links and the final commit SHA. Do not mark the handover gate complete while a P0 data-integrity, research-validity, security, or reproducibility blocker remains.

A green CI run is necessary but not sufficient for real-dataset validity, independent security acceptance, customer OT segmentation validation, or production safety acceptance.
