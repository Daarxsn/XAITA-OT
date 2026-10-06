"""Non-destructive local smoke test for XAITA-OT."""
from pathlib import Path
import tempfile
from xaita_ot.config import load_config
from xaita_ot.pipeline.demo import demo_events, make_demo_csv
from xaita_ot.pipeline.engine import XAITAEngine
from xaita_ot.cti.generator import write_json


def main() -> int:
    cfg = load_config()
    with tempfile.TemporaryDirectory(prefix="xaita-smoke-") as temp_dir:
        root = Path(temp_dir)
        csv_path = root / "swat_like.csv"
        cti_path = root / "smoke_cti.json"
        make_demo_csv(str(csv_path), 3000, cfg.seed)
        incidents = XAITAEngine(cfg).analyze_events(demo_events())
        write_json(incidents, cti_path)
        if not cti_path.is_file() or not incidents:
            raise RuntimeError("smoke test produced no incidents or artifact")
        print(f"Smoke OK: {len(incidents)} incident(s) -> {cti_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
