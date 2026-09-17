# BATADAL provenance and benchmark gate

## Purpose

XAITA-OT must keep BATADAL raw sensor files outside the public repository. Research runs must record provenance locally before benchmark evaluation is enabled.

## Required local manifest

Generate a manifest with:

```bash
PYTHONPATH=src python scripts/validate_batadal.py \
  --root data/raw/batadal \
  --output experiments/manifests/batadal.json
```

The manifest must include, for every subset:

- Dataset and subset name
- Original filename and local relative path
- SHA-256 hash
- File size
- Row and column counts
- Timestamp column and label column
- First and last timestamp
- Sampling frequency
- Native label values
- Unknown label values, including `-999` where present

## Attack metadata requirements

The interval metadata must include:

- Training Dataset 2 attacks 1–7
- Test Dataset attacks 8 onward
- Exact source reference for every row
- Start and end timestamps
- Duration reported by the official source
- Attack description and SCADA concealment details where available

## Gate policy

Benchmark evaluation remains **CLOSED** until:

1. The complete official test attack list is confirmed.
2. Raw-file SHA-256 hashes are recorded.
3. Dataset versions and acquisition dates are recorded.
4. Timestamp alignment passes validation.
5. Native labels and interval-derived labels are reported separately.
6. The research run records the exact manifest and configuration used.

Demo fixtures and screenshot-derived metadata are useful for engineering tests but do not constitute real-dataset benchmark evidence.
