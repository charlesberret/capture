from __future__ import annotations

import pytest

from capture.core import config, state


@pytest.fixture
def disabled_provider_config(monkeypatch: pytest.MonkeyPatch, tmp_path):
    test_config = {
        "defaults": {
            "tags": ["[[kernel]]", "[[captured]]"],
            "author": "",
        },
        "llm": {
            "content_threshold": 0,
            "enable_metis": False,
        },
        "providers": {
            stage: {"default": "disabled", "disabled": {}}
            for stage in (
                "transcription",
                "ocr",
                "title",
                "tags",
                "correction",
                "connections",
            )
        },
    }
    monkeypatch.setattr(config, "_config", test_config)
    monkeypatch.setattr(state, "NOTES_DIR", tmp_path)
    return test_config
