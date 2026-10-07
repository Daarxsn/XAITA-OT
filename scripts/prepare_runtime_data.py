"""Prepare private runtime datasets for XAITA-OT deployments.

Raw benchmark files must not be committed to the public repository. Datasets may
instead be supplied as mounted directories, local ZIP archives, or private ZIP
archive URLs. A single project-level ZIP can contain all three datasets under
SWaT/, BATADAL/ and TON-IoT/ (or data/raw/<dataset>/) and will be safely
extracted into the configured runtime dataset paths.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
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
        "default": "/app/data/raw/swat",
        "tokens": {"swat"},
    },
    "BATADAL": {
        "path_env": "XAITA_BATADAL_PATH",
        "archive_env": "XAITA_BATADAL_ARCHIVE",
        "url_env": "XAITA_BATADAL_ARCHIVE_URL",
        "sha_env": "XAITA_BATADAL_ARCHIVE_SHA256",
        "default": "/app/data/raw/batadal",
        "tokens": {"batadal"},
    },
    "TON-IoT": {
        "path_env": "XAITA_TONIOT_PATH",
        "archive_env": "XAITA_TONIOT_ARCHIVE",
        "url_env": "XAITA_TONIOT_ARCHIVE_URL",
        "sha_env": "XAITA_TONIOT_ARCHIVE_SHA256",
        "default": "/app/data/raw/ton_iot",
        "tokens": {"ton-iot", "ton_iot", "toniot"},
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


def _normalized_parts(name: str) -> list[str]:
    return [
        part.strip().lower().replace("-", "_")
        for part in Path(name.replace("\\", "/")).parts
        if part not in {"", "."}
    ]


def _is_symlink(member: zipfile.ZipInfo) -> bool:
    mode = (member.external_attr >> 16) & 0o170000
    return mode == 0o120000


def safe_extract(
    archive: Path,
    destination: Path,
    *,
    members: list[zipfile.ZipInfo] | None = None,
) -> int:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        selected = members if members is not None else bundle.infolist()
        total = 0
        for member in selected:
            if _is_symlink(member):
                raise RuntimeError(f"Unsafe symlink archive member: {member.filename}")
            total += member.file_size
            if total > MAX_ARCHIVE_BYTES:
                raise RuntimeError("Selected archive content exceeds XAITA_MAX_DATASET_ARCHIVE_BYTES")
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
        for member in selected:
            bundle.extract(member, destination)
        return len(selected)


def _archive_contains_dataset(member_names: list[str], dataset: str) -> bool:
    tokens = DATASETS[dataset]["tokens"]
    for name in member_names:
        parts = _normalized_parts(name)
        stem = Path(name).stem.strip().lower().replace("-", "_")
        if any(token in parts or stem == token or stem.startswith(f"{token}_") for token in tokens):
            return True
    return False

def _matching_members(bundle: zipfile.ZipFile, dataset: str, *, allow_all: bool) -> list[zipfile.ZipInfo]:
    infos = bundle.infolist()
    if allow_all:
        return infos
    tokens = DATASETS[dataset]["tokens"]
    return [
        info for info in infos
        if any(part in tokens for part in _normalized_parts(info.filename))
    ]


def _has_csv(root: Path) -> bool:
    return root.is_file() and root.suffix.lower() == ".csv" or (
        root.is_dir() and any(root.rglob("*.csv"))
    )


def _local_archive_candidates(dataset: str) -> list[Path]:
    spec = DATASETS[dataset]
    candidates: list[Path] = []
    for env in (spec["archive_env"], GENERIC_ARCHIVE_ENV):
        value = os.environ.get(env, "").strip()
        if value:
            candidates.append(Path(value))
    for base in (Path.cwd(), Path("/app")):
        candidates.extend([
            base / "datasets.zip",
            base / "data" / "datasets.zip",
            base / "data" / "raw" / "datasets.zip",
        ])
    return list(dict.fromkeys(path for path in candidates if path.is_file()))


def _verify_archive(archive: Path, expected_sha: str) -> None:
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise RuntimeError(
            f"Dataset archive exceeds XAITA_MAX_DATASET_ARCHIVE_BYTES: {archive}"
        )
    if expected_sha and sha256(archive).lower() != expected_sha.lower():
        raise RuntimeError(f"Dataset archive SHA-256 does not match expected digest: {archive}")


def _prepare_from_archive(
    archive: Path,
    dataset: str,
    destination: Path,
    *,
    expected_sha: str,
    dataset_specific: bool,
) -> bool:
    _verify_archive(archive, expected_sha)
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        names = [info.filename for info in infos]
        if dataset_specific:
            members = infos
        else:
            if not _archive_contains_dataset(names, dataset):
                return False
            members = _matching_members(bundle, dataset, allow_all=False)
        if not members:
            return False
        safe_extract(archive, destination, members=members)
        return _has_csv(destination)


def _download_archive(url: str, destination: Path) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "XAITA-OT-runtime/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def prepare_dataset(dataset: str) -> tuple[Path, str]:
    spec = DATASETS[dataset]
    root = Path(os.environ.get(spec["path_env"], spec["default"]))
    if _has_csv(root):
        return root, "mounted"

    root.mkdir(parents=True, exist_ok=True)
    expected_sha = os.environ.get(spec["sha_env"], os.environ.get(GENERIC_SHA_ENV, "")).strip()

    local_candidates = _local_archive_candidates(dataset)
    for archive in local_candidates:
        dataset_specific = bool(os.environ.get(spec["archive_env"], "").strip()) and archive == Path(
            os.environ[spec["archive_env"]]
        )
        if _prepare_from_archive(
            archive, dataset, root,
            expected_sha=expected_sha,
            dataset_specific=dataset_specific,
        ):
            return root, f"archive:{archive}"

    url = os.environ.get(spec["url_env"], "").strip()
    if not url:
        return root, "unavailable"

    with tempfile.TemporaryDirectory(prefix=f"xaita-{dataset.lower().replace('-', '')}-") as temp_dir:
        archive = _download_archive(url, Path(temp_dir) / "dataset.zip")
        _verify_archive(archive, expected_sha)
        if not _prepare_from_archive(
            archive, dataset, root,
            expected_sha=expected_sha,
            dataset_specific=True,
        ):
            raise RuntimeError(f"{dataset}: archive downloaded but contains no usable CSV dataset")
    return root, f"url:{url}"


def preflight_archive(archive: Path, output: Path | None = None) -> dict:
    """Inspect a project ZIP and validate every supported dataset in isolation.

    Extraction happens only in a temporary directory. The archive itself and
    repository working tree are never modified.
    """
    archive = Path(archive)
    if not archive.is_file():
        raise FileNotFoundError(f"Dataset archive not found: {archive}")
    _verify_archive(archive, "")
    with tempfile.TemporaryDirectory(prefix="xaita-dataset-preflight-") as temp_dir:
        temp_root = Path(temp_dir)
        results: dict[str, dict] = {}
        with zipfile.ZipFile(archive) as bundle:
            names = [item.filename for item in bundle.infolist()]
        for dataset in DATASETS:
            destination = temp_root / dataset.lower().replace("-", "_")
            try:
                extracted = _prepare_from_archive(
                    archive, dataset, destination, expected_sha="", dataset_specific=False
                )
                if not extracted:
                    results[dataset] = {
                        "present": False, "ready": False, "file_count": 0,
                        "validated_files": 0, "review_files": 0,
                        "reason": "No matching dataset content found in archive",
                    }
                    continue
                from xaita_ot.io.dataset_validation import build_manifest
                manifest = build_manifest(dataset, destination)
                results[dataset] = {
                    "present": True, "ready": bool(manifest["benchmark_validation_ready"]),
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
            "archive": {"path": str(archive), "size_bytes": archive.stat().st_size, "sha256": sha256(archive), "member_count": len(names)},
            "datasets": results,
            "all_ready": bool(results) and all(item["ready"] for item in results.values()),
        }
        if output is not None:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

def main() -> int:
    failures: list[str] = []
    for dataset in DATASETS:
        try:
            root, source = prepare_dataset(dataset)
            ready = _has_csv(root)
            print(f"{dataset}: ready={ready} root={root} source={source}")
            if not ready:
                print(f"{dataset}: no dataset CSV found; provide a mounted directory or ZIP archive")
        except Exception as exc:
            failures.append(f"{dataset}: {type(exc).__name__}: {exc}")

    if failures:
        for failure in failures:
            print(f"Runtime dataset preparation warning: {failure}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
