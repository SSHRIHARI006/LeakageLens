"""AuditConfig validation tests (spec 5.1/5.4/5.5)."""
from __future__ import annotations

import pandas as pd
import pytest

from leakagelens import AuditConfig


def test_default_config_is_valid():
    AuditConfig(target="target").validate()


@pytest.mark.parametrize("task", ["clustering", "", None])
def test_unsupported_task_rejected(task):
    with pytest.raises(ValueError, match="Unsupported task"):
        AuditConfig(target="target", task=task).validate()


@pytest.mark.parametrize("context", ["future", "", None])
def test_unsupported_inference_context_rejected(context):
    with pytest.raises(ValueError, match="inference_context"):
        AuditConfig(target="target", inference_context=context).validate()


@pytest.mark.parametrize("strategy", ["stratified", "", None])
def test_unsupported_split_strategy_rejected(strategy):
    with pytest.raises(ValueError, match="split strategy"):
        AuditConfig(target="target", original_strategy=strategy).validate()


def test_empty_target_rejected():
    with pytest.raises(ValueError, match="target column is required"):
        AuditConfig(target="").validate()


def test_declared_columns_must_exist(clean_frame):
    with pytest.raises(ValueError, match="group_column.*not found"):
        AuditConfig(target="target", group_column="customer").validate(clean_frame)
    with pytest.raises(ValueError, match="time_column.*not found"):
        AuditConfig(target="target", time_column="date").validate(clean_frame)


def test_group_or_time_cannot_be_target(clean_frame):
    with pytest.raises(ValueError, match="differ from the target"):
        AuditConfig(target="target", group_column="target").validate(clean_frame)
    with pytest.raises(ValueError, match="differ from the target"):
        AuditConfig(target="target", time_column="target", inference_context="temporal").validate(clean_frame)


def test_validate_frame_rejects_unsupported_task(clean_frame):
    from leakagelens.ingestion import validate_frame

    with pytest.raises(ValueError, match="Unsupported task"):
        validate_frame(clean_frame, "target", task="ranking")


def test_config_accepts_supported_columns(clean_frame):
    AuditConfig(target="target", group_column="segment").validate(clean_frame)
