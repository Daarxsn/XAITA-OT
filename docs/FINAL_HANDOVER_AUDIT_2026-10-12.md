# XAITA-OT Final Handover Audit

**Audit date:** 12 October 2026  
**Repository:** https://github.com/Daarxsn/XAITA-OT  
**Audited baseline:** `main` at merge commit `16260e255b4e1b28ebc5a10cafe26fbf86160f01`  
**Package version:** 0.5.1  
**Purpose:** Pre-handover repository, dashboard, API, data-validation, research-evidence, installation, and security review.

## 1. Executive result

The repository baseline has a substantial automated test suite and CI coverage. The most recent verified local regression run available for the merged benchmark/reproducibility change reported **253 tests passed, 15 non-fatal warnings**. GitHub Actions for that change reported success for the CI matrix (Python 3.11 and 3.12), clean-install workflows, dependency audit, security-posture checks, operational checks, provenance checks, and preflight checks.

This confirms that the repository passes its configured synthetic-fixture and code-contract checks. It **does not** confirm that every privately supplied benchmark dataset is correctly labeled, ready for supervised training, or has been evaluated with real-data results. That boundary matters for a scientific or company handover.

Final handover hardening was merged as PR #28, merge commit `b9acbb38b2cae59ba02069673e62bc8fe0109365`. Local startup now binds to loopback by default, and Compose publishes its host port on loopback by default. The container process listens on its container interface so local host-to-container forwarding works. PR #28 CI, clean-install, release-candidate, dependency/security evidence, operational, provenance, and preflight checks passed. The corresponding main-branch workflows were queued/running immediately after merge and should be checked in Actions for the final post-merge status.

## 2. Confirmed fixes already merged

The benchmark-validation/reproducibility change merged in PR #27 (`16260e2`) includes validation manifests, reproducibility identity, regression coverage, and selectable dataset subsets in the experiment-matrix CLI. The local full test run reported 253 passed.

The prior handover hardening in PR #26 (`4272189`) is also merged. GitHub Actions associated with the PR #27 head reported success for the configured CI matrix and the following checks:
- automated tests and smoke/acceptance scripts on Python 3.11 and 3.12;
- clean-install and release-candidate checks on Python 3.11 and 3.12;
- dependency vulnerability audit;
- container/filesystem security scan and Python static analysis;
- operational, security-posture, provenance, and preflight checks.

PR #28 then passed the same principal gates: CI (Python 3.11/3.12), V5 clean install, release candidate, dependency/security evidence, security posture, operational check, provenance, and preflight. PR #28 is merged. Main-branch workflows were running immediately after the merge; verify their final state in [GitHub Actions](https://github.com/Daarxsn/XAITA-OT/actions).

These are repository/fixture acceptance results; they are not independently reproduced real benchmark performance.

## 3. Issues found and their disposition

| Area | Finding | Disposition |
|---|---|---|
| Local server exposure | `run_api.py` used `0.0.0.0` by default, unnecessarily exposing a developer-run API to other interfaces on the machine/network. | Fixed in PR #28, merged as `b9acbb3`; default is `127.0.0.1`. A deployment must explicitly set `XAITA_HOST` to use another bind address. |
| Container port exposure | Compose published `8080:8080`, which binds on all host interfaces by default. | Fixed in PR #28, merged as `b9acbb3`; host publication is `127.0.0.1:8080:8080`. Remote publication now requires an explicit deployment change. |
| Raw dataset versioning | Benchmark files are deliberately excluded from Git; a source ZIP alone cannot include the user's licensed/private data. | Intentional and retained. Supply datasets separately, follow their access terms, and keep hashes/manifests alongside research outputs. |
| Dataset presence vs readiness | API/dashboard file-presence status is not the same as benchmark validation. | Dashboard contract tests cover this distinction; do not treat file presence as benchmark acceptance. |
| BATADAL labels | A dataset file includes native `ATT_FLAG=-999` unknown/unlabeled rows; the general validator flags them before the BATADAL attack-interval alignment can necessarily be applied. The test file may also lack a native label column. | Remains open. The ingest/validation sequence needs a dataset-aware policy using published attack interval metadata, with unknown labels preserved rather than silently changed to normal. |
| SWaT 2015 | The supplied consolidated CSV passed the generic validator. | Validation-ready for the structural contract checked; this does not by itself establish model performance or the correctness of every source's labeling semantics. Real four-detector run remains to be recorded. |
| SWaT A8 | 36 files were discovered but reviewed rather than marked ready; initial 1970 timestamps and empty annotation/attack columns were observed. | Remains open. Verify export schema and label provenance first. Detector output columns are not ground truth unless documented as such by the dataset source. Treat as exploratory/unlabeled until resolved. |
| TON-IoT | The supplied family has mixed data types: some IoT CSVs contain separate date/time columns and repeated timestamps; network/Linux/Windows files often lack native timestamp columns. | Remains open. Add family-specific validation and split policy; preserve synthetic event-order semantics and avoid claiming temporal generalization for data without native time. |
| Dashboard operational data | Some incident, asset and workflow panels use clearly marked illustrative/static demo scenarios; live event telemetry is not exposed by the dashboard API. | Do not present the static scenarios as live plant telemetry. Dashboard/API contract tests protect the explicit demo boundary in several panels; visual acceptance on recipient machines is still recommended. |
| Authentication | API auth is configurable; development defaults are intended for local use. | With loopback defaults, suitable for local handover/testing. For remote/shared deployments, configure production environment, strong API key/role, host allowlist, HTTPS/reverse proxy, and docs policy before exposure. |
| Process lifecycle | Experiment deadlines bound the HTTP wait but Python worker threads cannot be forcibly terminated. Lifecycle state is process-local. | Known design boundary. Use process isolation and external durable job storage for production requirements that need hard cancellation, multi-worker coordination, or persistence across restarts. |
| Release packaging | Dataset files and local experiment artifacts are excluded from source control. | Expected. Deliver the code archive separately from any licensed dataset archive; never commit private raw data to Git. |

## 4. Dataset audit status observed during this handover

These findings refer to the supplied local data and are not statements about every upstream distribution of each benchmark.

| Dataset path/family | Observed result | Safe interpretation |
|---|---|---|
| SWaT 2015 consolidated CSV | 1 file, structural validation passed | Can be the first real-data acceptance candidate; run and retain detector outputs before reporting scores. |
| SWaT A8 export | 36 files, all require review | Not a validated supervised benchmark input yet. Placeholder timestamps and absent/empty label columns need source-specific resolution. |
| BATADAL | 1 of 3 data CSVs passed; test missing native label, second training file contains `-999` values | Needs attack-interval alignment and explicit handling of unknown labels before the real experiment runner. |
| TON-IoT | 13 files, all require review under current generic validator | Needs family-specific schema and timestamp handling. Do not combine incompatible event families without a written protocol. |

## 5. Strong checks completed

- Local regression suite: **253 passed, 15 warnings** (15 warnings were non-fatal; inspect them when relevant, but they did not fail the test run).
- GitHub Actions on PR #27 head: CI Python 3.11/3.12 successful.
- GitHub Actions on PR #27 head: clean install Python 3.11/3.12 successful.
- Dependency audit, security-posture/SAST/container checks, operational, provenance and preflight jobs: successful.
- Dashboard contract tests explicitly look for escaped API-derived HTML, absence of random live telemetry, demo labeling, and distinction between dataset file presence and benchmark validation.
- Package contains Docker/Compose deployment, API health/readiness routes, API docs, configurable authentication/role controls, rate limiting and request-size controls.

The audit tool did not independently rerun the Windows-only 253-test command within the current editing environment; the 253-pass result is from the supplied recent local run, and the CI status was retrieved from GitHub Actions. The pending audit branch must be checked separately after CI completes.

## 6. Remaining work in priority order

### P0 — Before making real benchmark performance claims
1. Finish BATADAL native/interval label alignment, including unknown-label accounting and tests.
2. Define a per-family TON-IoT input contract and document where timestamps are native versus reconstructed from row order.
3. Resolve SWaT A8 timestamp/annotation provenance and preserve missing labels as unknown.
4. Execute a real-data detector suite on each accepted dataset; save input SHA-256, validation manifests, seed, config, code revision, and run outputs.
5. Inspect metric plausibility, split boundaries, duplicates/groups, class balance, and leakage risk before interpreting high scores.

### P1 — Before remote/shared use
1. Complete the final audit-branch CI run and merge only after it is green.
2. Configure remote authentication/secrets, HTTPS, trusted hosts, allowed origins, docs exposure, and external bind explicitly.
3. Test dashboard loading, API readiness, authentication and experiment lifecycle on a clean Windows machine with no developer-specific paths.
4. Package a separate private dataset archive only where data rights permit, and verify archive SHA-256/preflight before use.

### P2 — Gradual hardening
1. Use OS-process workers or a job queue if hard cancellation and persistent/multi-worker job state are required.
2. Add independent visual accessibility/browser checks and a clean-user handover walkthrough.
3. Add dataset-family-specific schemas/validators with small representative licensed fixtures.
4. Record final real-data run evidence and limitations in a new dated release record rather than changing the status of old benchmark artifacts.

## 7. Handover run path

### Windows PowerShell: local code/dashboard smoke

From the extracted source directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python -m xaita_ot.cli synthetic-data
python -m xaita_ot.cli demo
python run_api.py
```

Open `http://127.0.0.1:8080/`; API docs are at `http://127.0.0.1:8080/docs`. The dashboard's demo workflow is illustrative, not live plant telemetry. The ZIP does not contain private/raw SWaT, BATADAL or TON-IoT data.

### First defensible real-data acceptance

Start with the structurally passing SWaT 2015 file. Validate it, then run the four-detector suite only against that exact file, store the result and retain its dataset SHA-256. Do not call the overall three-dataset matrix complete until BATADAL and TON-IoT have passed their dataset-specific gates and all requested detectors complete.

## 8. Sign-off boundary

**Safe to hand over as:** research/analyst-support software with a runnable dashboard/API, demo scenarios clearly distinguished from live telemetry, automated synthetic-fixture CI, reproducibility and dataset-validation tooling, plus a documented plan for unresolved real-dataset integration.

**Not yet substantiated as:** a fully validated three-benchmark real-data release, a live plant telemetry dashboard, a production OT/ICS deployment, or certified/independently reproduced detector performance.

This report records observed repository and local-dataset findings as of 12 October 2026. All real-data claims should be tied to immutable input hashes and run artifacts.
