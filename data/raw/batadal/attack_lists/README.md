# BATADAL attack-list evidence

Store the original official BATADAL attack-list source files or screenshots here.

Required evidence:

- Training Dataset 2 attack list: attacks 1–7
- Test Dataset attack list: attacks 8 onward

Do not infer timestamps from screenshots or manually approximate intervals. The structured CSV files below must be transcribed from the official source and reviewed before use:

- `training_dataset_2_attacks.csv`
- `test_dataset_attacks.csv`

Suggested schema:

```text
attack_id,start_time,end_time,duration_hours,description,scada_concealment,labelled_hours,source_reference
```

Keep the original source evidence and record the source URL/reference in every structured row. These files are research metadata, not raw sensor data.
