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
