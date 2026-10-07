# XAITA-OT V5 — Day 47 Dataset Preflight & Research Data Readiness Lock

**Status:** COMPLETE / LOCKED

## Scope

Day 47 establishes a non-destructive preflight gate for the private SWaT, BATADAL and TON-IoT project archive introduced in Day 46. The gate answers whether the supplied archive actually contains each dataset family and whether the contained CSVs pass the same real-data validation contract used by experiments.

## Problem addressed

Day 46 established archive delivery, but did not provide a single safe command to inspect an actual private ZIP before extraction into the working tree or before expensive model training.

## Delivered

- Added packaged `xaita_ot.io.dataset_archive` preflight implementation so the feature works from a clean release wheel.
- Added `xaita preflight-dataset-archive --archive <zip> --out <report>` CLI command.
- Preflight inspects SWaT, BATADAL and TON-IoT independently.
- Extraction occurs only in a temporary workspace.
- Working-tree `data/raw` directories are never modified by preflight.
- Archive SHA-256 and member count are recorded.
- Dataset family presence, file count, validated files and review files are reported.
- Existing real-data validator remains the source of truth for CSV readiness.
- Missing or invalid families return `review` / exit code `2`; they are never silently treated as benchmark-ready.
- Packaging regression fixed: the CLI no longer imports an un-packaged `scripts.*` module.
- Added regression tests for packaged preflight, non-destructive behavior, deterministic archive identity and multi-dataset readiness.
- Documentation updated with the Day 47 preflight workflow.

## Command

```powershell
xaita preflight-dataset-archive --archive datasets.zip --out artifacts/dataset_preflight.json
```

Exit semantics:

- `0` — SWaT, BATADAL and TON-IoT are all present and validation-ready.
- `2` — one or more dataset families are missing or require review.
- `1` — archive inspection itself failed.

## Acceptance

1. Packaged CLI preflight command exists — PASS.
2. SWaT presence/readiness is independently reported — PASS.
3. BATADAL presence/readiness is independently reported — PASS.
4. TON-IoT presence/readiness is independently reported — PASS.
5. Archive SHA-256 is recorded — PASS.
6. Preflight is non-destructive — PASS.
7. Existing validation contract is reused — PASS.
8. Missing/invalid data fails closed — PASS.
9. Clean wheel installation works on Python 3.11 — PASS.
10. Clean wheel installation works on Python 3.12 — PASS.
11. Full CI/release matrix passes — PASS.

## Verification boundary

No claim is made that the user's private `datasets.zip` contains valid real benchmark data until that exact archive is supplied and preflight returns `all_ready=true`. Day 47 validates the delivery/readiness mechanism; it does not fabricate or substitute benchmark data.

## Locked baseline

Day 46 final lock: `5fc02b2d84bd0452b4f60bcf8ef3383a60b267c8`

## Final lock

Day 47 is locked only at the final green `main` commit after the complete release matrix.
