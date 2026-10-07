"""Config load: env > file > platform defaults. Offline; no live models."""

from __future__ import annotations

import pytest

from capture.core.config import load_config


@pytest.fixture(autouse=True)
def _clean_capture_env(monkeypatch):
    for key in ("OLLAMA_MODEL", "EDITOR", "CAPTURE_METIS", "CAPTURE_CONFIG"):
        monkeypatch.delenv(key, raising=False)


def _write_cfg(path, text: str):
    path.write_text(text)


def test_builtin_defaults_when_file_is_empty(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    _write_cfg(cfg_path, "notes_dir: ~/Notes\n")
    loaded = load_config(cfg_path)
    assert loaded["providers"]["title"]["default"] == "ollama_local"
    assert loaded["providers"]["title"]["ollama_local"]["host"] == "http://127.0.0.1:11434"
    assert loaded["providers"]["connections"]["default"] == "keyword"
    assert loaded["editor"] == "nano"


def test_file_overrides_stage_default(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    _write_cfg(
        cfg_path,
        "providers:\n  title:\n    default: truncate\n",
    )
    loaded = load_config(cfg_path)
    assert loaded["providers"]["title"]["default"] == "truncate"
    assert loaded["providers"]["tags"]["default"] == "ollama_local"


def test_ollama_model_env_overrides_every_ollama_stage(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    _write_cfg(cfg_path, "providers:\n  title:\n    ollama_local:\n      model: file-model\n")
    monkeypatch.setenv("OLLAMA_MODEL", "env-model")
    loaded = load_config(cfg_path)
    for stage in ("title", "tags", "correction"):
        assert loaded["providers"][stage]["ollama_local"]["model"] == "env-model"
    assert loaded["llm"]["model"] == "env-model"


def test_editor_env_overrides_file(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    _write_cfg(cfg_path, "editor: vim\n")
    monkeypatch.setenv("EDITOR", "ed")
    loaded = load_config(cfg_path)
    assert loaded["editor"] == "ed"


def test_capture_metis_false_disables_tags_and_connections(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    _write_cfg(cfg_path, "notes_dir: ~/Notes\n")
    monkeypatch.setenv("CAPTURE_METIS", "false")
    loaded = load_config(cfg_path)
    assert loaded["llm"]["enable_metis"] is False
    assert loaded["providers"]["tags"]["default"] == "disabled"
    assert loaded["providers"]["connections"]["default"] == "disabled"


def test_legacy_llm_block_fills_ollama_model(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    _write_cfg(cfg_path, "llm:\n  model: legacy-tag\n  enable_metis: false\n")
    loaded = load_config(cfg_path)
    assert loaded["providers"]["title"]["ollama_local"]["model"] == "legacy-tag"
    assert loaded["providers"]["tags"]["default"] == "disabled"
    assert loaded["providers"]["connections"]["default"] == "disabled"
