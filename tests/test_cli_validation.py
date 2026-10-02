from pathlib import Path

from xaita_ot.cli import build_parser, main


def test_cli_exposes_validate_data():
    parser = build_parser()
    args = parser.parse_args(["validate-data", "--dataset", "SWaT", "--root", "data/raw/swat"])
    assert args.cmd == "validate-data"
    assert args.dataset == "SWaT"


def test_cli_validate_data_writes_manifest(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    (root / "sample.csv").write_text(
        "Timestamp,Attack State,value\n"
        "2026-01-01 00:00:00,Normal,1.0\n"
        "2026-01-01 00:00:01,Attack,2.0\n",
        encoding="utf-8",
    )
    output = tmp_path / "manifest.json"
    assert main([
        "validate-data",
        "--dataset", "SWaT",
        "--root", str(root),
        "--out", str(output),
    ]) == 0
    assert output.is_file()
    assert '"benchmark_validation_ready": true' in output.read_text(encoding="utf-8")
