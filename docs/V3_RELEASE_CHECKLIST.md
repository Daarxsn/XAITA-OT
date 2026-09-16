# XAITA-OT V3.0 Release Checklist

**Release:** V3.0 Real-Dataset Research Validation  
**Status:** `OPEN — RESEARCH GATE NOT CLOSED`  
**Branch:** `main`

## Definition of completion

V3.0 is complete only when the research claims are supported by reproducible runs on authorized real datasets, with fixed dataset versions/hashes, leakage-safe partitions, statistical analysis, ablations, sensitivity analysis, cross-environment evaluation and a reproducibility package.

Demo fixtures are necessary for engineering regression but cannot satisfy the V3 real-dataset evidence gate.

## V3 status

| Requirement | Status | Completion evidence required |
|---|---:|---|
| V3 scope defined | ✅ | This release gate and evaluation protocol are committed. |
| Demo fixtures available | ✅ | Existing deterministic SWaT-like, BATADAL-like and TON-IoT-like fixtures. |
| Real benchmark evidence | ⏸️ OPEN | Authorized real SWaT, BATADAL and TON-IoT data; source/release, hashes, preprocessing manifest, run logs and result artifacts. |
| Statistical evaluation | ⏸️ OPEN | Repeated seeds, confidence intervals, baseline comparisons and uncertainty reporting. |
| Ablation/sensitivity evidence | ⏸️ OPEN | Detector/attribution component ablations and sensitivity to thresholds, windows and weights. |
| Reproducibility package | ⏸️ OPEN | Pinned environment, dataset manifest, commands, configs, seeds, outputs and rerun instructions. |
| Research gate formally closed | ❌ | Cannot close until every open evidence item is reviewed and attached. |

## Required real-dataset protocol

1. Obtain each dataset under its applicable terms and keep raw files outside source control.
2. Record dataset name, release/version, source, acquisition date, file names and SHA-256 hashes.
3. Validate timestamp, label, asset, protocol and feature semantics for the exact release.
4. Use chronological or attack-episode-aware 70/15/15 partitions.
5. Fit preprocessing only on the training partition.
6. Keep complete attack episodes in one partition; do not leak windows across partitions.
7. Run the declared detector and attribution matrices with fixed configurations and seeds.
8. Store raw predictions, metrics, runtime, configuration, provenance and environment metadata.
9. Report confidence intervals and uncertainty; do not report demo fixtures as benchmark results.
10. Review all claims against the recorded evidence before closing this gate.

## Research claim boundary

Until this checklist is closed, XAITA-OT must not claim validated benchmark performance, cross-environment generalization, ground-truth actor-attribution accuracy or publication-grade statistical conclusions.

## Lock decision

The V3 scope is defined, but the research gate remains **OPEN**. This document is a control against prematurely marking unsupported research claims as complete.
