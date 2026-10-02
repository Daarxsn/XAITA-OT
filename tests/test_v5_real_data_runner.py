from pathlib import Path

import scripts.v5_validate_local_datasets as runner


def test_configured_roots_use_environment_overrides(tmp_path, monkeypatch):
    swat = tmp_path / "swat"
    batadal = tmp_path / "batadal"
    toniot = tmp_path / "ton_iot"
    for path in (swat, batadal, toniot):
        path.mkdir()
    monkeypatch.setenv("XAITA_SWAT_PATH", str(swat))
    monkeypatch.setenv("XAITA_BATADAL_PATH", str(batadal))
    monkeypatch.setenv("XAITA_TONIOT_PATH", str(toniot))
    assert runner.configured_roots() == {
        "SWaT": swat,
        "BATADAL": batadal,
        "TON-IoT": toniot,
    }


def test_runner_writes_bundle_for_valid_fixture_roots(tmp_path, monkeypatch):
    roots = {}
    fixtures = {
        "SWaT": ("Timestamp,Attack State,x\n2026-01-01 00:00:00,Normal,1\n2026-01-01 00:00:01,Attack,2\n"),
        "BATADAL": ("DATETIME,ATT_FLAG,x\n01/01/2026 00:00,0,1\n01/01/2026 01:00,1,2\n"),
        "TON-IoT": ("date,time,label,x\n01-Jan-26,00:00:00,0,1\n01-Jan-26,00:00:01,1,2\n"),
    }
    envs = {"SWaT": "XAITA_SWAT_PATH", "BATADAL": "XAITA_BATADAL_PATH", "TON-IoT": "XAITA_TONIOT_PATH"}
    for dataset, csv in fixtures.items():
        root = tmp_path / dataset
        root.mkdir()
        (root / "sample.csv").write_text(csv, encoding="utf-8")
        roots[dataset] = root
        monkeypatch.setenv(envs[dataset], str(root))
    output = tmp_path / "bundle.json"
    assert runner.main(["--out", str(output)]) == 0
    assert output.is_file()
