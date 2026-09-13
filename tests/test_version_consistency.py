from importlib.metadata import version

import xaita_ot


def test_runtime_version_matches_distribution_metadata() -> None:
    assert xaita_ot.__version__ == version("xaita-ot")
