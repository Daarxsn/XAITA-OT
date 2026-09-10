"""Unified V2 controlled experiment runner.

The runner never substitutes synthetic values for missing benchmark datasets. Detection
runs use the supplied dataset path. Attribution configurations are executed against a
controlled evidence fixture derived from the completed detection run; this validates
ACFM/ablation machinery but is NOT an actor-attribution benchmark.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.evaluation import attribution_ablation
from xaita_ot.pipeline.experiments import run_detection, aggregate_runs, experiment_contract


def _attribution_fixture(run):
    """Create a deterministic evidence fixture from measured detector metrics."""
    cnn_lstm = run.metrics.get("cnn_lstm", {})
    dc = float(cnn_lstm.get("f1", 0.0))
    precision = float(cnn_lstm.get("precision", 0.0))
    recall = float(cnn_lstm.get("recall", 0.0))
    auc = cnn_lstm.get("auroc", 0.0)
    auc = 0.0 if not isinstance(auc, (int, float)) else float(auc)
    return {
        "H1": {"DC": dc, "BSS": precision, "ECS": recall, "EC": auc, "MAS": (dc + precision) / 2.0},
        "H2": {"DC": max(0.0, 1.0 - dc), "BSS": max(0.0, 1.0 - precision), "ECS": max(0.0, 1.0 - recall), "EC": max(0.0, 1.0 - auc), "MAS": 0.40},
        "H3": {"DC": 0.50, "BSS": 0.50, "ECS": 0.50, "EC": 0.50, "MAS": 0.50},
    }


def main():
    p = argparse.ArgumentParser(description="Run XAITA-OT V2 controlled experiments")
    p.add_argument("--swat")
    p.add_argument("--batadal")
    p.add_argument("--toniot")
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--out", default="artifacts/v2/experiment_manifest.json")
    args = p.parse_args()
    cfg = load_config(args.config)
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    manifest = {
        "schema_version": "XAITA-OT-V2-MANIFEST-2.0",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "config": cfg.model_dump(mode="json"),
        "contract": experiment_contract("multi-dataset", cfg.seed),
        "datasets": {},
    }
    all_runs = []
    for dataset, csv_path in paths.items():
        if not csv_path:
            manifest["datasets"][dataset] = {"status": "not_provided"}
            continue
        if not Path(csv_path).exists():
            manifest["datasets"][dataset] = {"status": "blocked_data", "path": str(csv_path)}
            continue
        runs = []
        for seed in cfg.experiment.seeds:
            run = run_detection(csv_path, dataset, cfg, seed)
            evidence = _attribution_fixture(run)
            reliability = {"DC": 0.90, "BSS": 0.85, "ECS": 0.80, "EC": 0.75, "MAS": 0.70}
            ablation = attribution_ablation(evidence, list(evidence), reliability)
            item = run.__dict__.copy()
            item["attribution"] = {
                "status": "controlled_evidence_validation",
                "methods": list(ablation.keys()),
                "results": {
                    name: [getattr(a, "__dict__", a) for a in values]
                    for name, values in ablation.items()
                },
            }
            runs.append(item)
            all_runs.append(run)
        manifest["datasets"][dataset] = {"status": "completed", "runs": runs}
    manifest["aggregate_detection"] = aggregate_runs(all_runs)["aggregate"]
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, allow_nan=False, default=str), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
