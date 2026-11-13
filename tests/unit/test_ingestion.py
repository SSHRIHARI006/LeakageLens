"""Ingestion and dataframe-profile tests (spec 5.1)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leakagelens.ingestion import load_table, profile, validate_frame


@pytest.fixture
def csv_frame(tmp_path):
    frame = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"], "target": [0, 1, 0]})
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    return path, frame


def test_csv_roundtrip_values_and_shape(csv_frame):
    path, expected = csv_frame
    loaded = load_table(path)
    assert loaded.shape == expected.shape
    pd.testing.assert_frame_equal(loaded, expected)


def test_xlsx_roundtrip(tmp_path):
    pytest.importorskip("openpyxl")
    frame = pd.DataFrame({"a": [1, 2], "target": [0, 1]})
    path = tmp_path / "data.xlsx"
    frame.to_excel(path, index=False)
    pd.testing.assert_frame_equal(load_table(path), frame)


def test_parquet_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    frame = pd.DataFrame({"a": [1.5, 2.5], "target": [0, 1]})
    path = tmp_path / "data.parquet"
    frame.to_parquet(path, index=False)
    pd.testing.assert_frame_equal(load_table(path), frame)


def test_extension_is_case_insensitive(tmp_path):
    frame = pd.DataFrame({"a": [1, 2], "target": [0, 1]})
    path = tmp_path / "DATA.CSV"
    frame.to_csv(path, index=False)
    assert len(load_table(path)) == 2


def test_unsupported_extension_and_missing_path(tmp_path):
    bad = tmp_path / "data.txt"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="Unsupported"):
        load_table(bad)
    with pytest.raises(FileNotFoundError):
        load_table(tmp_path / "absent.csv")


def test_empty_file_and_empty_frame(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    with pytest.raises(ValueError, match="no data"):
        load_table(empty)
    with pytest.raises(ValueError, match="empty"):
        validate_frame(pd.DataFrame())


def test_duplicate_csv_headers_rejected(tmp_path):
    path = tmp_path / "dup.csv"
    path.write_text("a,a,target\n1,2,0\n")
    with pytest.raises(ValueError, match="duplicate column names"):
        load_table(path)


def test_duplicate_dataframe_columns_rejected():
    frame = pd.DataFrame(np.arange(6).reshape(3, 2), columns=["a", "a"])
    with pytest.raises(ValueError, match="duplicate column names"):
        validate_frame(frame)


def test_missing_target_rejected(clean_frame):
    with pytest.raises(ValueError, match="not found"):
        validate_frame(clean_frame, "missing")


def test_target_with_missing_values_rejected():
    frame = pd.DataFrame({"x": [1, 2, 3], "target": [0, None, 1]})
    with pytest.raises(ValueError, match="missing value"):
        validate_frame(frame, "target")


def test_single_class_classification_rejected():
    frame = pd.DataFrame({"x": [1, 2, 3], "target": [1, 1, 1]})
    with pytest.raises(ValueError, match="at least two"):
        validate_frame(frame, "target", "classification")
    # The same frame is a valid (constant) regression target.
    validate_frame(frame, "target", "regression")


def test_regression_target_must_be_numeric_and_finite():
    frame = pd.DataFrame({"x": [1, 2], "target": ["a", "b"]})
    with pytest.raises(ValueError, match="numeric"):
        validate_frame(frame, "target", "regression")
    frame = pd.DataFrame({"x": [1, 2], "target": [1.0, np.inf]})
    with pytest.raises(ValueError, match="non-finite"):
        validate_frame(frame, "target", "regression")


def test_profile_reports_missing_constant_and_all_null(clean_frame):
    frame = clean_frame.copy()
    frame["constant"] = 1
    frame["all_null"] = np.nan
    frame.loc[0, "age"] = np.nan
    result = profile(frame, "target")
    assert result["rows"] == len(frame)
    assert result["columns"] == len(frame.columns)
    assert result["missing_values"]["age"] == 1
    assert "constant" in result["constant_columns"]
    assert "all_null" in result["all_null_columns"]
    assert set(result["target_distribution"]) == {0, 1}
    assert "segment" in result["categorical_columns"]
    assert "age" in result["numerical_columns"]


def test_possible_id_columns_threshold():
    small = pd.DataFrame({"id": range(10), "dup": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1], "target": [0, 1] * 5})
    result = profile(small)
    assert "id" in result["possible_id_columns"]
    assert "dup" not in result["possible_id_columns"]
    large = pd.DataFrame({"id": range(200), "target": [0, 1] * 100})
    assert "id" in profile(large)["possible_id_columns"]


def test_missing_values_counted_with_dropna_false():
    frame = pd.DataFrame({"id": [1, 2, None, None], "target": [0, 1, 0, 1]})
    # id has 2 distinct non-null values out of 4 rows; dropna=False counts the null.
    assert "id" not in profile(frame)["possible_id_columns"]


def test_unicode_and_spaced_column_names_supported():
    frame = pd.DataFrame({"feature one": [1, 2, 3], "café": [3, 2, 1], "target": [0, 1, 0]})
    validate_frame(frame, "target")
    assert "café" in profile(frame)["numerical_columns"]


def test_non_default_index_is_preserved_and_supported(clean_frame):
    shuffled = clean_frame.sample(frac=1, random_state=3)
    assert not isinstance(shuffled.index, pd.RangeIndex) or not shuffled.index.equals(pd.RangeIndex(len(shuffled)))
    validate_frame(shuffled, "target")
    assert load_table_from_frame_for_profile(shuffled)["rows"] == len(shuffled)


def load_table_from_frame_for_profile(frame: pd.DataFrame) -> dict:
    return profile(frame, "target")
