"""Streamlit smoke tests (spec 8)."""
from __future__ import annotations

from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[2] / "ui" / "streamlit_app.py"


def test_app_loads_without_exception():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value == "LeakageLens"


def test_empty_state_explains_how_to_get_example_data():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert any("examples/generate_datasets.py" in block.value for block in at.info)
    assert any("not proof" in caption.value for caption in at.caption)
    assert any("not general similarity search" in caption.value for caption in at.caption)
