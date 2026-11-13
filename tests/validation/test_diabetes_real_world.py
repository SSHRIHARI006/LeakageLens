from pathlib import Path

import numpy as np
import pandas as pd

from leakagelens.detectors import exact_duplicates, group_overlap
from leakagelens.evaluation import make_split
from validation.real_world.diabetes_130.run_experiment import TARGET, feature_columns, load


def fixture() -> pd.DataFrame:
    return pd.DataFrame({
        "encounter_id": [1, 2, 3, 4], "patient_nbr": [10, 10, 20, 30],
        "race": ["C", "C", "A", "B"], "admission_type_id": [1, 1, 2, 2],
        "readmitted": ["NO", "<30", "NO", ">30"],
    })


def test_target_and_identifier_policy(tmp_path: Path):
    source = tmp_path / "diabetic_data.csv"
    fixture().to_csv(source, index=False)
    frame = load(source)
    assert frame[TARGET].tolist() == [0, 1, 0, 0]
    assert "encounter_id" not in feature_columns(frame, "admission")
    assert "patient_nbr" not in feature_columns(frame, "admission")


def test_group_split_has_zero_patient_overlap():
    frame = fixture().assign(**{TARGET: [0, 1, 0, 0]})
    train, test = make_split(frame, TARGET, "classification", 42, group="patient_nbr", strategy="group")
    assert set(frame.iloc[train].patient_nbr) & set(frame.iloc[test].patient_nbr) == set()
    assert group_overlap(frame, "patient_nbr", train, test) == []


def test_exact_cross_split_control_is_detected():
    frame = fixture().assign(**{TARGET: [0, 1, 0, 0]})
    injected = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    train = np.array([0, 1, 2, 3])
    test = np.array([4])
    findings = exact_duplicates(injected, TARGET, train, test)
    assert any(f.category == "split_contamination" for f in findings)
