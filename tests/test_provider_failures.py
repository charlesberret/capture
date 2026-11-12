"""Title provider failures surface on stderr and in frontmatter; truncate still works."""

from __future__ import annotations

import json
import urllib.error

import pytest
import yaml

from capture.core import state
from capture.core.config import set_config
from capture.core.note import create_note, generate_title
from capture.core.provider_failure import begin_title_capture, consume_title_provider_failure


def ollama_title_config(notes_dir):
    return {
        "notes_dir": str(notes_dir),
        "capture_dir": str(notes_dir / "_capture-staging"),
        "whisper_dictionary": None,
        "editor": "nano",
        "llm": {
            "model": "qwen-capable",
            "enable_metis": False,
            "title_timeout": 60,
            "tag_timeout": 45,
            "content_threshold": 10,
            "whisper_model": "medium",
            "whisper_backend": "python",
            "auto_correct": False,
            "correction_timeout": 90,
        },
        "defaults": {"tags": ["kernel", "captured"], "author": ""},
        "metis": {
            "serendipity_age_days": 30,
            "max_connections": 3,
            "max_keywords": 10,
        },
        "ui": {"max_recent": 5},
        "providers": {
            "transcription": {"default": "disabled", "disabled": {}},
            "ocr": {"default": "disabled", "disabled": {}},
            "title": {
                "default": "ollama_local",
                "ollama_local": {
                    "model": "qwen-capable",
                    "host": "http://127.0.0.1:11434",
                    "timeout": 5,
                },
                "truncate": {},
            },
            "tags": {"default": "disabled", "disabled": {}},
            "correction": {"default": "disabled", "disabled": {}},
            "connections": {"default": "disabled", "disabled": {}},
        },
    }


@pytest.fixture
def ollama_title_notes(tmp_path):
    import capture.core.config as config_mod

    set_config(ollama_title_config(tmp_path))
    state.NOTES_DIR = tmp_path
    yield tmp_path
    config_mod._config = None
    state.NOTES_DIR = None


CONTENT = "A long enough captured thought for the title provider."


def truncate_title(content: str) -> str:
    return content.split("\n")[0].strip()[:50].strip()


def _stderr(capsys):
    return capsys.readouterr().err


def test_connection_refused_fallback_and_stderr(monkeypatch, ollama_title_notes, capsys):
    def refuse(*_args, **_kwargs):
        raise urllib.error.URLError(ConnectionRefusedError())

    monkeypatch.setattr("capture.providers.ollama_http.post_json", refuse)
    path = create_note(CONTENT)
    fm = yaml.safe_load(path.read_text().split("---", 2)[1])
    assert fm["title"] == truncate_title(CONTENT)
    assert fm["title_fallback"] == "ollama_local: connection refused"
    err = _stderr(capsys)
    assert err.strip() == "capture: title provider ollama_local: connection refused"


def test_http_error_fallback_and_stderr(monkeypatch, ollama_title_notes, capsys):
    def http_error(*_args, **_kwargs):
        raise RuntimeError("HTTP 503: model not found")

    monkeypatch.setattr("capture.providers.ollama_http.post_json", http_error)
    path = create_note(CONTENT)
    fm = yaml.safe_load(path.read_text().split("---", 2)[1])
    assert fm["title_fallback"] == "ollama_local: HTTP 503"
    err = _stderr(capsys)
    assert "HTTP 503" in err


def test_malformed_json_fallback_and_stderr(monkeypatch, ollama_title_notes, capsys):
    def bad_json(*_args, **_kwargs):
        raise json.JSONDecodeError("Expecting value", "", 0)

    monkeypatch.setattr("capture.providers.ollama_http.post_json", bad_json)
    path = create_note(CONTENT)
    fm = yaml.safe_load(path.read_text().split("---", 2)[1])
    assert fm["title_fallback"] == "ollama_local: malformed JSON"
    err = _stderr(capsys)
    assert "malformed JSON" in err


def test_timeout_fallback_and_stderr(monkeypatch, ollama_title_notes, capsys):
    def slow(*_args, **_kwargs):
        raise TimeoutError()

    monkeypatch.setattr("capture.providers.ollama_http.post_json", slow)
    path = create_note(CONTENT)
    fm = yaml.safe_load(path.read_text().split("---", 2)[1])
    assert fm["title_fallback"] == "ollama_local: timeout"
    assert fm["title"] == truncate_title(CONTENT)
    err = _stderr(capsys)
    assert "timeout" in err


def test_failure_reported_once_per_capture(monkeypatch, ollama_title_notes, capsys):
    calls = {"n": 0}

    def refuse(*_args, **_kwargs):
        calls["n"] += 1
        raise urllib.error.URLError(ConnectionRefusedError())

    monkeypatch.setattr("capture.providers.ollama_http.post_json", refuse)
    begin_title_capture()
    slug = generate_title(CONTENT)
    consume_title_provider_failure()
    err = _stderr(capsys)
    assert slug == truncate_title(CONTENT)
    assert err.count("capture: title provider") == 1
    assert calls["n"] == 1
