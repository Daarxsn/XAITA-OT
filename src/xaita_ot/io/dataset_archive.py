"""Non-destructive private benchmark archive inspection.

This module is packaged with XAITA-OT so the CLI works from a clean wheel
installation. Raw benchmark data is never written to the repository.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path


DATASET_TOKENS = {
    "SWaT": {"swat"},
    "BATADAL": {"batadal"},
    "TON-IoT": {"ton-iot", "ton_iot", "toniot"},
}
MAX_ARCHIVE_BYTES = 50 * 1024**3


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parts(name: str) -> list[str]:
    return [
        part.strip().lower().replace("-", "_")
        for part in Path(name.replace("\\", "/")).parts
        if part not in {"", "."}
    ]


def _symlink(member: zipfile.ZipInfo) -> bool:
    return ((member.external_attr >> 16) & 0o170000) == 0o120000


def _safe_extract_selected(bundle: zipfile.ZipFile, members: list[zipfile.ZipInfo], destination: Path) -> None:
    destination = destination.resolve()
    total = 0
    for member in members:
        if _symlink(member):
            raise RuntimeError(f"Unsafe symlink archive member: {member.filename}")
        total += member.file_size
        if total > MAX_ARCHIVE_BYTES:
            raise RuntimeError("Selected archive content exceeds preflight size limit")
        target = (destination / member.filename).resolve()
        if target != destination and destination not in target.parents:
            raise RuntimeError(f"Unsafe archive member: {member.filename}")
    destination.mkdir(parents=True, exist_ok=True)
    for member in members:
        bundle.extract(member, destination)


def _contains(names: list[str], dataset: str) -> bool:
    tokens = DATASET_TOKENS[dataset]
    for name in names:
        parts = _parts(name)
        stem = Path(name).stem.strip().lower().replace("-", "_")
        if any(token in parts or stem == token or stem.startswith(f"{token}_") for token in tokens):
            return True
    return False


def _members_for(bundle: zipfile.ZipFile, dataset: str) -> list[zipfile.ZipInfo]:
    tokens = DATASET_TOKENS[dataset]
    result = []
    for member in bundle.infolist():
        parts = _parts(member.filename)
        stem = Path(member.filename).stem.strip().lower().replace("-", "_")
        if any(token in parts or stem == token or stem.startswith(f"{token}_") for token in tokens):
            result.append(member)
    return result


def preflight_archive(archive: str | Path, output: str | Path | None = None) -> dict:
    """Validate all three supported dataset families in a temporary workspace."""
    archive = Path(archive)
    if not archive.is_file():
        raise FileNotFoundError(f"Dataset archive not found: {archive}")
    size = archive.stat().st_size
    if size > MAX_ARCHIVE_BYTES:
        raise RuntimeError("Dataset archive exceeds the preflight size limit")

    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        names = [item.filename for item in infos]
        results: dict[str, dict] = {}
        with tempfile.TemporaryDirectory(prefix="xaita-preflight-") as temp_dir:
            root = Path(temp_dir)
            for dataset in DATASET_TOKENS:
                try:
                    if not _contains(names, dataset):
                        results[dataset] = {
                            "present": False, "ready": False, "file_count": 0,
                            "validated_files": 0, "review_files": 0,
                            "reason": "No matching dataset content found in archive",
                        }
                        continue
                    destination = root / dataset.lower().replace("-", "_")
                    members = _members_for(bundle, dataset)
                    _safe_extract_selected(bundle, members, destination)
                    from .dataset_validation import build_manifest
                    manifest = build_manifest(dataset, destination)
                    results[dataset] = {
                        "present": True,
                        "ready": bool(manifest["benchmark_validation_ready"]),
                        "file_count": manifest["file_count"],
                        "validated_files": manifest["validated_files"],
                        "review_files": manifest["review_files"],
                        "manifest_sha256": manifest["manifest_sha256"],
                    }
                except Exception as exc:
                    results[dataset] = {
                        "present": True, "ready": False, "file_count": 0,
                        "validated_files": 0, "review_files": 0,
                        "reason": f"{type(exc).__name__}: {exc}",
                    }

    payload = {
        "schema_version": "XAITA-OT-V5-DATASET-PREFLIGHT-1.0",
        "archive": {
            "path": str(archive),
            "size_bytes": size,
            "sha256": _sha256(archive),
            "member_count": len(infos),
        },
        "datasets": results,
        "all_ready": bool(results) and all(item["ready"] for item in results.values()),
    }
    if output is not None:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
