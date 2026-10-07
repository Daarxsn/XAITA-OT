"""Unlabeled SWaT telemetry analysis.

This module intentionally does not infer or manufacture attack labels. It runs
unsupervised anomaly analysis on researcher-supplied SWaT telemetry chunks and
produces auditable scores plus robust-deviation feature context.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


EXCLUDED_COLUMNS = {
    "timestamp",
    "annotation",
    "other anomalies",
    "attack hash",
    "attack name",
    "attack state",
    "label",
    "normal/attack",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_csvs(root: Path) -> list[Path]:
    seen: set[str] = set()
    files: list[Path] = []
    for path in sorted(root.rglob("*.csv"), key=lambda p: p.as_posix().lower()):
        digest = _sha256(path)
        if digest not in seen:
            seen.add(digest)
            files.append(path)
    return files


def _numeric_features(frame: pd.DataFrame) -> list[str]:
    features: list[str] = []
    for column in frame.columns:
        if str(column).strip().lower() in EXCLUDED_COLUMNS:
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().mean() >= 0.90 and converted.nunique(dropna=True) > 1:
            features.append(column)
    return features


def _top_deviations(
    values: np.ndarray,
    feature_names: list[str],
    medians: np.ndarray,
    scales: np.ndarray,
    top_n: int = 3,
) -> tuple[list[str], list[float]]:
    deviation = np.abs((values - medians) / scales)
    order = np.argsort(-deviation, axis=1)[:, :top_n]
    names: list[str] = []
    scores: list[float] = []
    for row in order:
        names.append("|".join(feature_names[i] for i in row))
        scores.append(float(deviation[row[0]]))
    return names, scores


def analyze_swat_unlabeled(
    root: str | Path,
    out: str | Path = "artifacts/swat_unlabeled",
    seed: int = 42,
    train_fraction: float = 0.70,
    max_train_rows: int = 20_000,
    n_estimators: int = 200,
    top_n: int = 3,
) -> dict[str, Any]:
    source_root = Path(root).resolve()
    output_root = Path(out)
    output_root.mkdir(parents=True, exist_ok=True)

    if not source_root.exists():
        raise ValueError(f"SWaT root not found: {source_root}")
    if not 0.1 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be in [0.1, 1.0)")
    if max_train_rows < 256:
        raise ValueError("max_train_rows must be at least 256")
    if n_estimators < 10:
        raise ValueError("n_estimators must be at least 10")

    files = _unique_csvs(source_root)
    if not files:
        raise ValueError(f"No CSV files found under {source_root}")

    file_results: list[dict[str, Any]] = []
    total_rows = 0
    total_flagged = 0

    for source in files:
        frame = pd.read_csv(source, low_memory=False)
        if frame.empty:
            continue

        features = _numeric_features(frame)
        if len(features) < 2:
            file_results.append({
                "file": source.relative_to(source_root).as_posix(),
                "sha256": _sha256(source),
                "status": "review",
                "reason": "fewer than two usable numeric telemetry features",
                "rows": len(frame),
                "feature_count": len(features),
            })
            continue

        numeric = pd.DataFrame(
            {
                column: pd.to_numeric(frame[column], errors="coerce")
                for column in features
            }
        )
        split = max(256, int(len(numeric) * train_fraction))
        split = min(split, len(numeric))
        train = numeric.iloc[:split].copy()

        medians = train.median()
        train = train.fillna(medians).replace([np.inf, -np.inf], np.nan)
        numeric = numeric.fillna(medians).replace([np.inf, -np.inf], np.nan)

        valid_columns = [
            column for column in features
            if train[column].notna().any() and float(train[column].std(ddof=0) or 0) > 0
        ]
        if len(valid_columns) < 2:
            file_results.append({
                "file": source.relative_to(source_root).as_posix(),
                "sha256": _sha256(source),
                "status": "review",
                "reason": "fewer than two variable numeric telemetry features",
                "rows": len(frame),
                "feature_count": len(valid_columns),
            })
            continue

        train = train[valid_columns]
        numeric = numeric[valid_columns]
        medians = train.median()
        scales = (train.quantile(0.75) - train.quantile(0.25)).replace(0, 1.0).fillna(1.0)

        X_train = train.to_numpy(dtype=np.float32)
        X_all = numeric.fillna(medians).to_numpy(dtype=np.float32)
        if len(X_train) > max_train_rows:
            rng = np.random.default_rng(seed)
            indices = rng.choice(len(X_train), size=max_train_rows, replace=False)
            X_train = X_train[np.sort(indices)]

        model = IsolationForest(
            n_estimators=n_estimators,
            max_samples="auto",
            contamination="auto",
            random_state=seed,
            n_jobs=-1,
        )
        model.fit(X_train)
        decision = model.decision_function(X_all)
        anomaly_score = -decision
        prediction = model.predict(X_all)
        flagged = prediction == -1

        names, deviation = _top_deviations(
            numeric.to_numpy(dtype=float),
            valid_columns,
            medians.to_numpy(dtype=float),
            scales.to_numpy(dtype=float),
            top_n=top_n,
        )

        scored = frame.copy()
        scored.insert(0, "source_row", np.arange(len(scored), dtype=int))
        scored["xaita_anomaly_score"] = anomaly_score
        scored["xaita_anomaly_flag"] = flagged.astype(int)
        scored["xaita_top_deviations"] = names
        scored["xaita_top_deviation_score"] = deviation

        relative = source.relative_to(source_root)
        destination = output_root / relative.parent / f"{relative.stem}_scored.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        scored.to_csv(destination, index=False)

        top_indices = np.argsort(-anomaly_score)[:10]
        top_rows = []
        for index in top_indices:
            timestamp = None
            for candidate in ("Timestamp", "timestamp", "time", "ts"):
                if candidate in frame.columns:
                    value = frame.iloc[index][candidate]
                    timestamp = None if pd.isna(value) else str(value)
                    break
            top_rows.append({
                "source_row": int(index),
                "timestamp_raw": timestamp,
                "anomaly_score": float(anomaly_score[index]),
                "top_deviations": names[index],
                "top_deviation_score": float(deviation[index]),
            })

        total_rows += len(frame)
        total_flagged += int(flagged.sum())
        file_results.append({
            "file": relative.as_posix(),
            "sha256": _sha256(source),
            "status": "completed",
            "rows": len(frame),
            "feature_count": len(valid_columns),
            "features": valid_columns,
            "train_rows": int(len(X_train)),
            "anomaly_rows": int(flagged.sum()),
            "anomaly_fraction": float(flagged.mean()),
            "scored_file": destination.as_posix(),
            "top_anomalies": top_rows,
        })

    payload: dict[str, Any] = {
        "schema_version": "XAITA-OT-SWAT-UNLABELED-ANALYSIS-1.0",
        "dataset": "SWaT",
        "analysis_mode": "unlabeled_unsupervised",
        "ground_truth_used": False,
        "ground_truth_inferred": False,
        "benchmark_metrics_available": False,
        "seed": seed,
        "algorithm": {
            "name": "IsolationForest",
            "n_estimators": n_estimators,
            "contamination": "auto",
            "train_fraction": train_fraction,
            "max_train_rows": max_train_rows,
        },
        "source_root": str(source_root),
        "unique_csv_count": len(files),
        "total_rows": total_rows,
        "total_anomaly_rows": total_flagged,
        "files": file_results,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["fingerprint"] = hashlib.sha256(canonical).hexdigest()
    summary_path = output_root / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload["summary"] = str(summary_path)
    return payload
