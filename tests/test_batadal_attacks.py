from pathlib import Path

import pandas as pd
import pytest

from xaita_ot.datasets.batadal_attacks import (
    BATADALAttackMetadataError,
    apply_attack_intervals,
    load_attack_intervals,
)


ROOT = Path(__file__).parents[1]
TRAINING_METADATA = ROOT / "data/raw/batadal/attack_lists/training_dataset_2_attacks.csv"


def test_training_attack_metadata_contains_seven_reviewed_rows():
    intervals = load_attack_intervals(TRAINING_METADATA)
    assert [item.attack_id for item in intervals] == list(range(1, 8))
    assert intervals[0].start_time == pd.Timestamp("2016-09-13 23:00")
    assert intervals[0].end_time == pd.Timestamp("2016-09-16 00:00")


def test_interval_alignment_is_inclusive_at_both_boundaries():
    intervals = load_attack_intervals(TRAINING_METADATA)
    frame = pd.DataFrame(
        {
            "DATETIME": [
                "2016-09-13 22:00",
                "2016-09-13 23:00",
                "2016-09-16 00:00",
                "2016-09-16 01:00",
            ],
            "ATT_FLAG": [0, -999, -999, 0],
        }
    )
    aligned = apply_attack_intervals(frame, intervals, "DATETIME")
    assert aligned["interval_attack_label"].tolist() == [0, 1, 1, 0]
    assert aligned["interval_attack_id"].tolist() == [pd.NA, 1, 1, pd.NA]
    assert aligned["ATT_FLAG"].tolist() == [0, -999, -999, 0]


def test_duplicate_attack_ids_are_rejected(tmp_path):
    path = tmp_path / "attacks.csv"
    path.write_text(
        "attack_id,start_time,end_time,duration_hours,description,scada_concealment,labelled_hours,source_reference\n"
        "1,2016-01-01 00:00,2016-01-01 01:00,2,a,b,1,source\n"
        "1,2016-01-02 00:00,2016-01-02 01:00,2,a,b,1,source\n",
        encoding="utf-8",
    )
    with pytest.raises(BATADALAttackMetadataError, match="duplicate attack_id"):
        load_attack_intervals(path)
