"""Prepare private runtime datasets for XAITA-OT deployments.

Raw benchmark files stay outside the public repository. Datasets can be mounted
or supplied through a private ZIP archive/URL. Extraction is delegated to the
package archive utility so CLI, API and container execution share one safety
contract.
"""
from __future__ import annotations

import os
import sys

from xaita_ot.io.dataset_archive import DATASETS, prepare_dataset


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
            print(f"Runtime dataset preparation failed: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
