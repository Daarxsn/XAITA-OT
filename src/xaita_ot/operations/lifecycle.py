"""Safe backup, recovery, retention and upgrade/rollback lifecycle primitives."""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "XAITA-OT-LIFECYCLE-BACKUP-1.0"
PLAN_SCHEMA = "XAITA-OT-LIFECYCLE-PLAN-1.0"
DEFAULT_EXCLUDES = {".git", ".venv", "__pycache__", ".pytest_cache"}
DEFAULT_RAW_PREFIX = Path("data/raw")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path, extra_excludes: set[Path] | None = None) -> list[Path]:
    found = []
    extra_excludes = {Path(item) for item in (extra_excludes or set())}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in DEFAULT_EXCLUDES for part in rel.parts):
            continue
        if rel.parts[:2] == DEFAULT_RAW_PREFIX.parts:
            continue
        if any(rel == excluded or excluded in rel.parents for excluded in extra_excludes):
            continue
        found.append(rel)
    return sorted(found)


def build_backup_manifest(root: str | Path, extra_excludes: set[Path] | None = None) -> dict[str, Any]:
    base = Path(root).resolve()
    if not base.is_dir():
        raise ValueError(f"backup root is not a directory: {base}")
    extra_excludes = {Path(item) for item in (extra_excludes or set())}
    files = [
        {"path": rel.as_posix(), "sha256": _sha256(base / rel), "size": (base / rel).stat().st_size}
        for rel in _files(base, extra_excludes)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "root_name": base.name,
        "excluded": sorted(DEFAULT_EXCLUDES | {"data/raw"} | {item.as_posix() for item in extra_excludes}),
        "files": files,
    }


def create_backup(root: str | Path, output: str | Path) -> Path:
    base = Path(root).resolve()
    destination = Path(output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    extra_excludes = set()
    try:
        output_parent = destination.parent.relative_to(base)
    except ValueError:
        output_parent = None
    if output_parent is not None:
        extra_excludes.add(output_parent)
    manifest = build_backup_manifest(base, extra_excludes=extra_excludes)
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "xaita-backup"
        stage.mkdir()
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        for item in manifest["files"]:
            source = base / item["path"]
            target = stage / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        with tarfile.open(destination, "w:gz") as archive:
            archive.add(stage, arcname="xaita-backup")
    return destination


def read_backup_manifest(backup: str | Path) -> dict[str, Any]:
    with tarfile.open(backup, "r:gz") as archive:
        try:
            member = archive.getmember("xaita-backup/manifest.json")
        except KeyError as exc:
            raise ValueError("backup is missing xaita-backup/manifest.json") from exc
        with archive.extractfile(member) as handle:
            if handle is None:
                raise ValueError("backup manifest cannot be read")
            return json.loads(handle.read().decode("utf-8"))


def _safe_member_path(name: str) -> Path:
    prefix = "xaita-backup/"
    if not name.startswith(prefix):
        raise ValueError(f"unexpected archive member: {name}")
    rel = Path(name[len(prefix):])
    if not rel.parts or rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe archive member path: {name}")
    return rel


def _validate_archive_members(archive: tarfile.TarFile, manifest: dict[str, Any]) -> None:
    if not isinstance(manifest.get("files"), list):
        raise ValueError("backup manifest files must be a list")
    manifest_paths = []
    for item in manifest["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("backup manifest contains an invalid file entry")
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts or not item.get("sha256") or len(str(item["sha256"])) != 64:
            raise ValueError("backup manifest contains an unsafe file entry")
        if rel.as_posix() in manifest_paths:
            raise ValueError(f"duplicate manifest path: {rel.as_posix()}")
        if "size" in item and (not isinstance(item["size"], int) or item["size"] < 0):
            raise ValueError(f"invalid manifest size for {rel.as_posix()}")
        manifest_paths.append(rel.as_posix())
    expected = {"manifest.json"} | set(manifest_paths)
    actual_files = set()
    seen_members = set()
    for member in archive.getmembers():
        if member.name in seen_members:
            raise ValueError(f"duplicate archive member: {member.name}")
        seen_members.add(member.name)
        if member.name == "xaita-backup":
            if not member.isdir():
                raise ValueError("backup root member must be a directory")
            continue
        rel = _safe_member_path(member.name)
        rel_name = rel.as_posix()
        if member.isdir():
            prefix = rel_name.rstrip("/") + "/"
            if not any(name.startswith(prefix) for name in expected):
                raise ValueError(f"unexpected archive directory: {member.name}")
            continue
        if rel_name not in expected:
            raise ValueError(f"unexpected archive member: {member.name}")
        if not member.isfile() or member.issym() or member.islnk() or not stat.S_ISREG(member.mode):
            raise ValueError(f"backup contains non-regular member: {member.name}")
        actual_files.add(rel_name)
    missing = expected - actual_files
    if missing:
        raise ValueError(f"backup is missing expected members: {sorted(missing)}")

def verify_backup(backup: str | Path) -> dict[str, Any]:
    manifest = read_backup_manifest(backup)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported lifecycle backup schema")
    failures = []
    with tarfile.open(backup, "r:gz") as archive:
        _validate_archive_members(archive, manifest)
        for item in manifest.get("files", []):
            member = f"xaita-backup/{item['path']}"
            with archive.extractfile(member) as handle:
                if handle is None:
                    failures.append(f"unreadable:{item['path']}")
                    continue
                digest = hashlib.sha256()
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != item["sha256"]:
                failures.append(f"checksum:{item['path']}")
    return {"schema_version": SCHEMA_VERSION, "verified": not failures, "file_count": len(manifest.get("files", [])), "failures": failures}


def restore_backup(backup: str | Path, staging_root: str | Path) -> Path:
    destination = Path(staging_root).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("restore destination must be empty; restore never overwrites a live root")
    destination.mkdir(parents=True, exist_ok=True)
    verification = verify_backup(backup)
    if not verification["verified"]:
        raise ValueError("refusing restore from failed backup verification")
    with tarfile.open(backup, "r:gz") as archive:
        manifest = read_backup_manifest(backup)
        _validate_archive_members(archive, manifest)
        for item in archive.getmembers():
            if item.name == "xaita-backup":
                continue
            rel = _safe_member_path(item.name)
            if rel == Path("manifest.json"):
                continue
            target = (destination / rel).resolve()
            if target != destination and destination not in target.parents:
                raise ValueError(f"unsafe restore target: {item.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(item)
            if source is not None:
                with target.open("wb") as output:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(chunk)
    return destination


def prune_backups(directory: str | Path, *, keep: int = 5) -> list[Path]:
    if keep < 1:
        raise ValueError("keep must be at least 1")
    base = Path(directory)
    backups = sorted(base.glob("xaita-backup-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = backups[keep:]
    for path in removed:
        path.unlink()
    return removed


def build_lifecycle_plan(*, current_revision: str, target_revision: str, backup_path: str, rollback_revision: str | None = None) -> dict[str, Any]:
    if not current_revision.strip() or not target_revision.strip() or not backup_path.strip():
        raise ValueError("current_revision, target_revision and backup_path are required")
    return {
        "schema_version": PLAN_SCHEMA,
        "current_revision": current_revision,
        "target_revision": target_revision,
        "rollback_revision": rollback_revision or current_revision,
        "backup_path": backup_path,
        "pre_upgrade": ["create_backup", "verify_backup", "record_current_revision"],
        "upgrade": ["deploy_target_revision", "run_health_check", "run_smoke_check"],
        "rollback": ["stop_new_revision", "restore_verified_backup_to_staging", "redeploy_previous_revision", "run_health_check"],
        "retention": {"policy": "retain newest backups; prune only after verification", "default_keep": 5},
        "autonomous_ot_action": False,
    }
