"""Risk aggregation tests (spec 5.8)."""
from __future__ import annotations

import pytest

from leakagelens.scoring import aggregate
from leakagelens.schemas import Finding


def finding(category: str, score: float) -> Finding:
    return Finding("test", category, "moderate", "medium", score, "title", "description")


def test_empty_findings_score_zero_and_low():
    assert aggregate([]) == (0.0, "LOW", {})


def test_single_category_expected_score():
    score, level, signals = aggregate([finding("a", 50)])
    assert score == 27.5
    assert signals == {"a": 50.0}
    assert level == "MODERATE"


def test_max_per_category_prevents_double_counting():
    score, _, signals = aggregate([finding("a", 50), finding("a", 90), finding("a", 20)])
    assert signals == {"a": 90.0}
    assert score == 49.5


def test_multiple_categories_sum_then_scale():
    score, _, signals = aggregate([finding("a", 40), finding("b", 60)])
    assert signals == {"a": 40.0, "b": 60.0}
    assert score == 55.0


def test_score_is_capped_at_100():
    score, level, _ = aggregate([finding(c, 100) for c in "abcd"])
    assert score == 100.0
    assert level == "CRITICAL"


def test_finding_scores_are_clamped():
    assert finding("a", -10).score == 0.0
    assert finding("a", 999).score == 100.0


@pytest.mark.parametrize("total,level", [(19.9, "LOW"), (20, "MODERATE"), (39.9, "MODERATE"), (40, "HIGH"), (69.9, "HIGH"), (70, "CRITICAL")])
def test_severity_levels(total, level):
    # Two categories let us reach high totals without clamping a single finding.
    low = min(total / .55, 100)
    remaining = max(0.0, total / .55 - low)
    findings = [finding("a", low)] + ([finding("b", remaining)] if remaining else [])
    assert aggregate(findings)[1] == level


def test_lower_score_in_existing_category_does_not_change_total():
    base = aggregate([finding("a", 60)])[0]
    assert aggregate([finding("a", 60), finding("a", 5)])[0] == base
