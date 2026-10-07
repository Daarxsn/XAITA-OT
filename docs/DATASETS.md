# Dataset Integration

XAITA-OT is designed around three benchmark environments used by the research paper: SWaT, BATADAL and TON-IoT. Dataset files must be obtained by the researcher under the applicable terms and placed outside source control.

## Common contract

Each adapter should expose at minimum:

- `timestamp`: parseable event time
- `label`: `0` benign / `1` attack for detection experiments
- numeric telemetry features
- optional `asset` and `protocol`

The semantic feature taxonomy follows the paper: temporal, network, protocol, statistical, asset, process, security and behavioral information.

## SWaT

Use `adapt_swat()` for common timestamp/label normalization. Verify the exact column names against the dataset release in use before running experiments.

## BATADAL

Use `adapt_batadal()` and validate timestamp/attack-label semantics against the selected BATADAL challenge release.

## TON-IoT

Use `adapt_toniot()` and validate the selected telemetry/network/security subset and label definition.

## Evaluation rule

Do not train on the complete dataset and report that score as a test result. Use chronological or attack-episode-aware 70/15/15 partitions, fit preprocessing only on training data, and retain attack episodes in one partition.


## Large private ZIP workflow

Raw benchmark datasets are intentionally excluded from Git. A large project-local archive can be used without committing its contents.

Expected layout:

```text
datasets.zip
├── SWaT/
│   └── <SWaT CSV files>
├── BATADAL/
│   └── <BATADAL CSV files>
└── TON-IoT/
    └── <TON-IoT CSV files>
```

The runtime preparation layer recognizes `XAITA_DATASET_ARCHIVE` and common local `datasets.zip` locations. It safely extracts only the selected dataset family into `data/raw/<dataset>` and rejects path-traversal and symlink archive members. A SHA-256 can be supplied with `XAITA_DATASET_ARCHIVE_SHA256`.

Dataset-specific archives are supported with `XAITA_SWAT_ARCHIVE`, `XAITA_BATADAL_ARCHIVE`, and `XAITA_TONIOT_ARCHIVE`, or their corresponding `*_ARCHIVE_URL` and `*_ARCHIVE_SHA256` settings.

For normal local startup:

```powershell
python run_api.py
```

`run_api.py` prepares available private/mounted archives before starting FastAPI. Missing datasets remain explicitly unavailable rather than being represented as benchmark evidence.

For Docker/Compose, mount the private archive into the container and set `XAITA_DATASET_ARCHIVE=/app/datasets.zip`. Raw datasets and archives remain outside source control. The API exposes all three dataset families, but an experiment is executable only when the selected dataset contains validated CSV data.
