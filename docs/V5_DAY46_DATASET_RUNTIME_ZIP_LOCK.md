# XAITA-OT V5.4 — Day 46 Dataset Runtime Availability & ZIP Support Lock

**Status:** COMPLETE / LOCKED

## Scope

Day 46 resolves the real-dataset runtime availability gap exposed by the analyst dashboard: only TON-IoT was selectable in the UI, while the API depended on raw benchmark directories that are intentionally absent from Git.

## Root cause confirmed

- The validation UI exposed only TON-IoT.
- `run_api.py` did not invoke the existing runtime dataset preparation layer.
- Runtime preparation previously supported only BATADAL archive configuration.
- SWaT and TON-IoT had no equivalent archive preparation path.
- `data/raw/swat` and `data/raw/ton_iot` are intentionally absent from source control; BATADAL contains repository scaffolding/metadata rather than the private benchmark CSVs.
- The repository correctly excludes raw benchmark data from Git.

## Delivered

- All three datasets are now supported by runtime archive preparation: SWaT, BATADAL and TON-IoT.
- A single private `datasets.zip` can contain all three dataset families.
- Dataset-specific private ZIPs and private archive URLs are supported.
- SHA-256 verification is supported for archive integrity.
- ZIP path-traversal and symlink members are rejected.
- Dataset-specific extraction prevents unrelated dataset content from being copied into another dataset root.
- `run_api.py` now prepares available private/mounted archives before starting FastAPI.
- The validation UI now exposes SWaT, BATADAL and TON-IoT.
- Unavailable dataset errors now identify the configured path and provide an actionable archive/mount hint.
- ZIP archives are explicitly ignored by Git to prevent accidental raw-data commits.
- Dataset/archive workflow documentation was added.
- Regression tests cover multi-dataset archive discovery, extraction, selective extraction and traversal protection.

## Expected project-local workflow

Place a private archive beside the project as `datasets.zip` with folders such as:

```text
SWaT/<csv files>
BATADAL/<csv files>
TON-IoT/<csv files>
```

Then run:

```powershell
python run_api.py
```

The runtime preparer extracts the available datasets into `data/raw/<dataset>`. Raw files remain ignored by Git. Experiments still require the selected dataset to pass the normal validation gate.

## Acceptance

1. SWaT selectable in validation UI — PASS.
2. BATADAL selectable in validation UI — PASS.
3. TON-IoT selectable in validation UI — PASS.
4. One private ZIP can provide all three dataset families — PASS.
5. Normal local API startup invokes preparation — PASS.
6. Docker/Compose archive configuration is exposed — PASS.
7. Raw archives remain outside Git — PASS.
8. Archive traversal/symlink protections are tested — PASS.
9. Missing datasets remain fail-closed and are never represented as benchmark evidence — PASS.
10. Full CI/release verification must pass before lock — PASS.

## Verification boundary

Day 46 fixes dataset delivery/runtime availability. It does not claim that the user's private ZIP actually contains valid SWaT, BATADAL or TON-IoT benchmark files until that archive is supplied and the dataset validation commands pass.

## Locked baseline

Day 45 parent: `aece34b4a2f2c35935f65820f3499dbc27ef0c91`

## Final lock

Day 46 is accepted on the final green `main` commit after the complete CI/release matrix.
