# XAITA-OT v5 — Day 2 Functional Data-Layer Completion

**Date:** 2026-09-27  
**Day 1 baseline:** `f03501d7c3723cac461c82792422e3062d4dbefc`  
**Day 2 functional commits:** `a859d1b`, `8b1fa83`

## Day 2 objective

Complete and lock the dataset-adapter layer required for real SWaT, BATADAL and TON-IoT execution. The key blocker discovered during delivery preparation was that supplied SWaT CSV exports use an `Attack State` column and can encode attacks as both boolean and numeric states, while the canonical adapter previously only considered generic `Attack`/`label` aliases.

## Completed

### 1. SWaT label normalization fixed

The SWaT adapter now recognizes `Attack State` in addition to existing label aliases. The canonical normalization treats benign values (`False`, `0`, `0.0`, `normal`, `benign`, empty and equivalent null text) as benign and populated non-benign states as attacks.

This covers the heterogeneous values observed in the supplied SWaT A8 data, including `True`, `5.0`, `7.0` and `2.0`.

### 2. Cross-dataset canonical contract preserved

The adapter continues to produce the canonical `timestamp`, `label`, `asset`, `protocol`, `src_ip` and `dst_ip` fields through the existing taxonomy/adapter path.

### 3. Regression test added

A dedicated test now proves that SWaT values `False`, `True`, `5.0`, `7.0` and empty normalize to `[0, 1, 1, 1, 0]`.

Existing SWaT/BATADAL/TON-IoT adapter coverage remains intact.

## Dataset execution boundary

The application already resolves deployment dataset paths through environment overrides or conventional local paths and exposes readiness through `/v2/datasets`. The runtime does not require raw benchmark data to be committed to Git. This is intentional for redistribution/licensing and deployment hygiene.

The Windows delivery environment has separately been verified by the delivery workflow to contain ready paths for all three datasets; those local files are not part of this repository commit.

## Acceptance checklist

- [x] SWaT adapter recognizes `Attack State`.
- [x] SWaT boolean attack values normalize correctly.
- [x] SWaT numeric attack states normalize correctly.
- [x] SWaT empty/false values remain benign.
- [x] BATADAL adapter contract remains covered.
- [x] TON-IoT adapter contract remains covered.
- [x] Regression test committed.
- [x] Dataset paths remain deployment-configurable.
- [x] Benchmark raw data remains outside source control.

## Important verification boundary

GitHub-side code changes cannot execute against Purvesh's Windows-local datasets or local API process. Therefore Day 2 is locked as **code/data-layer completion**, while the actual full detector execution, model training and end-to-end API acceptance remain a Day 3 runtime gate on the Windows deployment environment.

This distinction is deliberate: a repository commit cannot honestly claim a local Windows training run passed unless that run has actually been executed and observed.

## Day 2 scope lock

No new dataset family is added to v5 during the remaining delivery cycle unless required by the locked v5 acceptance criteria. Further work moves to detector execution, end-to-end pipeline validation, resource protection, uncertainty semantics and company-grade runtime hardening.
