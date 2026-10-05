import json
from pathlib import Path

import pytest

from xaita_ot.cli import main
from xaita_ot.operations.lifecycle import (
    SCHEMA_VERSION,
    build_backup_manifest,
    build_lifecycle_plan,
    create_backup,
    prune_backups,
    restore_backup,
    verify_backup,
)


def test_backup_verify_and_restore_are_checksum_bound(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "configs").mkdir()
    (root / "configs" / "app.yaml").write_text("mode: test\n", encoding="utf-8")
    (root / "data" / "raw").mkdir(parents=True)
    (root / "data" / "raw" / "restricted.csv").write_text("must-not-backup", encoding="utf-8")

    manifest = build_backup_manifest(root)
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert "configs/app.yaml" in {x["path"] for x in manifest["files"]}
    assert "data/raw/restricted.csv" not in {x["path"] for x in manifest["files"]}

    backup = create_backup(root, tmp_path / "xaita-backup-001.tar.gz")
    verified = verify_backup(backup)
    assert verified["verified"] is True

    restored = restore_backup(backup, tmp_path / "restore")
    assert (restored / "configs" / "app.yaml").read_text(encoding="utf-8") == "mode: test\n"


def test_restore_refuses_non_empty_destination(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "app.txt").write_text("safe", encoding="utf-8")
    backup = create_backup(root, tmp_path / "xaita-backup-001.tar.gz")
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "existing.txt").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        restore_backup(backup, staging)


def test_lifecycle_plan_has_explicit_rollback_and_retention():
    plan = build_lifecycle_plan(
        current_revision="old",
        target_revision="new",
        backup_path="backup.tar.gz",
    )
    assert plan["schema_version"] == "XAITA-OT-LIFECYCLE-PLAN-1.0"
    assert plan["rollback_revision"] == "old"
    assert plan["retention"]["default_keep"] == 5
    assert plan["autonomous_ot_action"] is False
    assert "verify_backup" in plan["pre_upgrade"]


def test_prune_keeps_newest_backups(tmp_path):
    for index in range(4):
        path = tmp_path / f"xaita-backup-{index}.tar.gz"
        path.write_text(str(index), encoding="utf-8")
        path.touch()
    removed = prune_backups(tmp_path, keep=2)
    assert len(removed) == 2
    assert len(list(tmp_path.glob("xaita-backup-*.tar.gz"))) == 2


def test_lifecycle_cli(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "config.txt").write_text("v1", encoding="utf-8")
    backup = tmp_path / "xaita-backup.tar.gz"
    plan = tmp_path / "plan.json"

    assert main(["backup", "--root", str(root), "--out", str(backup)]) == 0
    assert main(["backup-verify", "--backup", str(backup)]) == 0
    assert main([
        "lifecycle-plan", "--current-revision", "v1", "--target-revision", "v2",
        "--backup", str(backup), "--out", str(plan),
    ]) == 0
    assert json.loads(plan.read_text())["rollback_revision"] == "v1"
