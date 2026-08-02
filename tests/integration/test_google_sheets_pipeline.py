"""Tests for the Google Sheets sync pipeline.

STAGE 1 NOTE: storage/google_sheets_adapter.py is a documented
placeholder (see docs/ROADMAP.md, Stage 2). This test only confirms
the module imports cleanly; real pipeline tests will be added once the
adapter exists and a live/sandboxed Sheets connection is available.
"""

import importlib


def test_google_sheets_adapter_module_imports_without_error():
    module = importlib.import_module(
        "prediction_markets_lab.storage.google_sheets_adapter"
    )
    assert module is not None
