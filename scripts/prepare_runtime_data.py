"""Prepare private runtime datasets for XAITA-OT deployments.

Raw benchmark files stay outside the public repository. Datasets can be mounted
or supplied through a private ZIP archive/URL. Extraction is delegated to the
package archive utility so CLI, API and container execution share one safety
contract.
"""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

from xaita_ot.io.dataset_archive import (
    DATASETS,
    _matches_name,
    _safe_extract_selected,
    _verify_archive,
    prepare_dataset,
    preflight_archive,
)


def _archive_contains_dataset(member_names, dataset):
    return any(_matches_name(name, dataset) for name in member_names)


def _has_csv(root):
    root = Path(root)
    return (root.is_file() and root.suffix.lower() == ".csv") or (
        root.is_dir() and any(root.rglob("*.csv"))
    )


def safe_extract(archive, destination, *, members=None):
    with zipfile.ZipFile(archive) as bundle:
        selected = members if members is not None else bundle.infolist()
        return _safe_extract_selected(bundle, selected, Path(destination))


def _prepare_from_archive(archive, dataset, destination, *, expected_sha, dataset_specific):
    archive = Path(archive)
    _verify_archive(archive, expected_sha)
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist() if dataset_specific else [
            item for item in bundle.infolist() if _matches_name(item.filename, dataset)
        ]
        if not members:
            return False
        safe_extract(archive, destination, members=members)
    return _has_csv(destination)


def main() -> int:
    failures: list[str] = []
    for dataset in DATASETS:
        try:
            root, source = prepare_dataset(dataset)
            ready = root.is_file() and root.suffix.lower() == ".csv" or (
                root.is_dir() and any(root.rglob("*.csv"))
            )
            print(f"{dataset}: ready={ready} root={root} source={source}")
            if not ready:
                print(
                    f"{dataset}: no dataset CSV found; provide a mounted directory "
                    "or private ZIP archive",
                    file=sys.stderr,
                )
        except Exception as exc:
            failures.append(f"{dataset}: {type(exc).__name__}: {exc}")

    if failures:
        for failure in failures:
            print(f"Runtime dataset preparation warning: {failure}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
