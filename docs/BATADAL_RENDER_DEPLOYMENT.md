# BATADAL on Render

## Security rule

BATADAL raw CSV files are private research data and must not be committed to this public repository.

## Supported deployment modes

### Mode A — Render persistent disk

Mount a Render persistent disk at:

```text
/var/data
```

Place the files at:

```text
/var/data/batadal/train_1/BATADAL_dataset03.csv
/var/data/batadal/train_2/BATADAL_dataset04.csv
/var/data/batadal/test/BATADAL_test_dataset.csv
```

Set the Render environment variable:

```text
XAITA_BATADAL_PATH=/var/data/batadal
```

### Mode B — Private archive at startup

Create a private ZIP archive with the BATADAL directory structure and configure:

```text
XAITA_BATADAL_PATH=/var/data/batadal
XAITA_BATADAL_ARCHIVE_URL=<private signed URL>
XAITA_BATADAL_ARCHIVE_SHA256=<sha256 of the ZIP>
```

The container downloads the archive before starting the API. A checksum mismatch or unsafe archive causes startup to fail closed.

## Verification

After redeployment:

```text
GET /health
GET /ready
GET /v2/datasets
```

The BATADAL entry must report:

```json
{
  "configured": true,
  "exists": true
}
```

Then open the dashboard and navigate to **05 · RESEARCH LAB**. Select BATADAL, choose a detector and seed, and execute an experiment.

## Production acceptance checks

- [ ] Render persistent disk or private archive configured
- [ ] `XAITA_BATADAL_PATH` points to the runtime directory
- [ ] All three CSV files exist
- [ ] Dataset hashes recorded in the provenance manifest
- [ ] `/v2/datasets` reports BATADAL available
- [ ] Research Lab executes a real BATADAL run
- [ ] Run response contains experiment ID, rows, windows, duration and metrics
- [ ] Raw CSV files are not present in Git history
- [ ] V3 statistical and cross-environment gates remain separate from deployment readiness
