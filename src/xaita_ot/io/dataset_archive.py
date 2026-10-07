"""Safe preparation and non-destructive preflight for private benchmark archives."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DATASETS = {
    "SWaT": {
        "path_env": "XAITA_SWAT_PATH",
        "archive_env": "XAITA_SWAT_ARCHIVE",
        "url_env": "XAITA_SWAT_ARCHIVE_URL",
        "sha_env": "XAITA_SWAT_ARCHIVE_SHA256",
        "default": "data/raw/swat",
        "tokens": {"swat"},
    },
    "BATADAL": {
        "path_env": "XAITA_BATADAL_PATH",
        "archive_env": "XAITA_BATADAL_ARCHIVE",
        "url_env": "XAITA_BATADAL_ARCHIVE_URL",
        "sha_env": "XAITA_BATADAL_ARCHIVE_SHA256",
        "default": "data/raw/batadal",
        "tokens": {"batadal"},
    },
    "TON-IoT": {
        "path_env": "XAITA_TONIOT_PATH",
        "archive_env": "XAITA_TONIOT_ARCHIVE",
        "url_env": "XAITA_TONIOT_ARCHIVE_URL",
        "sha_env": "XAITA_TONIOT_ARCHIVE_SHA256",
        "default": "data/raw/ton_iot",
        "tokens": {"ton_iot", "toniot", "ton-iot"},
    },
}

GENERIC_ARCHIVE_ENV = "XAITA_DATASET_ARCHIVE"
GENERIC_SHA_ENV = "XAITA_DATASET_ARCHIVE_SHA256"
MAX_ARCHIVE_BYTES = int(os.environ.get("XAITA_MAX_DATASET_ARCHIVE_BYTES", str(50 * 1024**3)))


def sha256(path: Path) -> str:
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


def _is_symlink(member: zipfile.ZipInfo) -> bool:
    return ((member.external_attr >> 16) & 0o170000) == 0o120000


def _matches_name(name: str, dataset: str) -> bool:
    tokens = DATASETS[dataset]["tokens"]
    parts = _parts(name)
    stem = Path(name).stem.strip().lower().replace("-", "_")
    if any(
        token in parts or stem == token or stem.startswith(f"{token}_")
        for token in tokens
    ):
        return True
    # Accept common benchmark files when the archive contains the dataset
    # directory contents without the parent directory name.
    if dataset == "TON-IoT" and stem in {
        "train_test_network",
        "train_test_iot_modbus",
        "train_test_iot_modbus_1",
        "train_test_iot_modbus_2",
    }:
        return True
    return False


def _matching_members(bundle: zipfile.ZipFile, dataset: str) -> list[zipfile.ZipInfo]:
    return [member for member in bundle.infolist() if _matches_name(member.filename, dataset)]


def _safe_extract_selected(
    bundle: zipfile.ZipFile,
    members: list[zipfile.ZipInfo],
    destination: Path,
) -> int:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    total = 0
    for member in members:
        if _is_symlink(member):
            raise RuntimeError(f"Unsafe symlink archive member: {member.filename}")
        total += member.file_size
        if total > MAX_ARCHIVE_BYTES:
            raise RuntimeError("Selected archive content exceeds XAITA_MAX_DATASET_ARCHIVE_BYTES")
        target = (destination / member.filename).resolve()
        if target != destination and destination not in target.parents:
            raise RuntimeError(f"Unsafe archive member: {member.filename}")
    for member in members:
        bundle.extract(member, destination)
    return len(members)


def _verify_archive(archive: Path, expected_sha: str = "") -> None:
    if not archive.is_file():
        raise FileNotFoundError(f"Dataset archive not found: {archive}")
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise RuntimeError(
            f"Dataset archive exceeds XAITA_MAX_DATASET_ARCHIVE_BYTES: {archive}"
        )
    if expected_sha and sha256(archive).lower() != expected_sha.lower():
        raise RuntimeError(f"Dataset archive SHA-256 does not match expected digest: {archive}")


def _has_csv(root: Path) -> bool:
    return (
        root.is_file() and root.suffix.lower() == ".csv"
    ) or (
        root.is_dir() and any(root.rglob("*.csv"))
    )


def _archive_candidates(dataset: str) -> list[Path]:
    spec = DATASETS[dataset]
    values = []
    for env in (spec["archive_env"], GENERIC_ARCHIVE_ENV):
        value = os.environ.get(env, "").strip()
        if value:
            values.append(Path(value))
    for base in (Path.cwd(), Path("/app")):
        values.extend([
            base / "datasets.zip",
            base / "data" / "datasets.zip",
            base / "data" / "raw" / "datasets.zip",
        ])
    return list(dict.fromkeys(path for path in values if path.is_file()))


def _download_archive(url: str) -> tuple[Path, tempfile.TemporaryDirectory]:
    temp_dir = tempfile.TemporaryDirectory(prefix="xaita-dataset-download-")
    destination = Path(temp_dir.name) / "dataset.zip"
    request = urllib.request.Request(url, headers={"User-Agent": "XAITA-OT-runtime/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except Exception:
        temp_dir.cleanup()
        raise
    # The temporary directory must stay alive until the caller finishes reading
    # the archive. Return it explicitly rather than attaching state to Path.
    return destination, temp_dir


def prepare_dataset(dataset: str, *, root: str | Path | None = None) -> tuple[Path, str]:
    """Materialize one dataset from a mounted path, private ZIP or private URL."""
    if dataset not in DATASETS:
        raise ValueError(f"Unsupported dataset: {dataset}")
    spec = DATASETS[dataset]
    destination = Path(
        os.environ.get(spec["path_env"], str(root) if root is not None else spec["default"])
    )
    if _has_csv(destination):
        return destination, "mounted"

    destination.mkdir(parents=True, exist_ok=True)
    expected_sha = os.environ.get(
        spec["sha_env"], os.environ.get(GENERIC_SHA_ENV, "")
    ).strip()

    for archive in _archive_candidates(dataset):
        explicit = os.environ.get(spec["archive_env"], "").strip()
        dataset_specific = bool(explicit) and archive == Path(explicit)
        _verify_archive(archive, expected_sha)
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist() if dataset_specific else _matching_members(bundle, dataset)
            if not members:
                continue
            _safe_extract_selected(bundle, members, destination)
        if _has_csv(destination):
            return destination, f"archive:{archive}"

    url = os.environ.get(spec["url_env"], "").strip()
    if url:
        archive, temp_dir = _download_archive(url)
        try:
            _verify_archive(archive, expected_sha)
            with zipfile.ZipFile(archive) as bundle:
                _safe_extract_selected(bundle, bundle.infolist(), destination)
            if _has_csv(destination):
                return destination, f"url:{url}"
        finally:
            temp_dir.cleanup()

    return destination, "unavailable"


def preflight_archive(archive: str | Path, output: str | Path | None = None) -> dict:
    """Inspect all supported dataset families without modifying the working tree."""
    archive = Path(archive)
    _verify_archive(archive)
    with zipfile.ZipFile(archive) as bundle:
        names = [item.filename for item in bundle.infolist()]
        results: dict[str, dict] = {}
        with tempfile.TemporaryDirectory(prefix="xaita-dataset-preflight-") as temp_dir:
            root = Path(temp_dir)
            for dataset in DATASETS:
                try:
                    members = _matching_members(bundle, dataset)
                    if not members:
                        results[dataset] = {
                            "present": False, "ready": False, "runnable": False,
                            "file_count": 0, "validated_files": 0, "review_files": 0,
                            "reason": "No matching dataset content found in archive",
                        }
                        continue
                    destination = root / dataset.lower().replace("-", "_")
                    _safe_extract_selected(bundle, members, destination)
                    from .dataset_validation import build_manifest
                    manifest = build_manifest(dataset, destination)
                    results[dataset] = {
                        "present": True,
                        "ready": bool(manifest["benchmark_validation_ready"]),
                        "runnable": bool(manifest["benchmark_validation_ready"]),
                        "file_count": manifest["file_count"],
                        "validated_files": manifest["validated_files"],
                        "review_files": manifest["review_files"],
                        "manifest_sha256": manifest["manifest_sha256"],
                    }
                except Exception as exc:
                    results[dataset] = {
                        "present": True, "ready": False, "runnable": False,
                        "file_count": 0, "validated_files": 0, "review_files": 0,
                        "reason": f"{type(exc).__name__}: {exc}",
                    }

    payload = {
        "schema_version": "XAITA-OT-V5-DATASET-PREFLIGHT-1.1",
        "archive": {
            "path": str(archive),
            "size_bytes": archive.stat().st_size,
            "sha256": sha256(archive),
            "member_count": len(names),
        },
        "datasets": results,
        "all_ready": bool(results) and all(item["ready"] for item in results.values()),
    }
    if output is not None:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
