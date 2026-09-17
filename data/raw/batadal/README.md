# BATADAL raw data

Place the officially downloaded BATADAL files in the directories below. Raw files are intentionally ignored by Git; do not commit or redistribute dataset contents.

```text
data/raw/batadal/
├── train_1/
│   └── BATADAL_dataset03.csv
├── train_2/
│   └── BATADAL_dataset04.csv
├── test/
│   └── BATADAL_test_dataset.csv
└── attack_lists/
    ├── training_dataset_2_attacks.*
    └── test_dataset_attacks.*
```

Keep the original downloaded archives and source attack-list screenshots locally. Record file hashes, acquisition dates, source URLs, and applicable usage terms in the experiment manifest. Do not edit the raw CSV files; normalization and label alignment must happen in the processing pipeline.
