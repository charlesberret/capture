"""Tests targeting the highest-risk coverage gaps (offline only)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from capture.core import state
from capture.core.config import resolve_secret, set_config
from capture.core.note import (
    _model_tag_for_note,
    create_note,
    slugify,
    surface_serendipity,
)
from capture.core.pipeline import ocr_image, transcribe_audio
from capture.core.prompts_loader import format_prompt, load_prompt
from capture.core.vocabulary import (
    apply_corrections,
    build_whisper_prompt,
    flatten_vocabulary,
    load_whisper_dictionary,
)
from capture.providers.connections.keyword import KeywordConnectionsProvider
from capture.providers.enrich.ollama import OllamaTitleProvider
from tests.test_capture_floor import disabled_config


@pytest.fixture
def offline(tmp_path):
    import capture.core.config as config_mod

    set_config(disabled_config(tmp_path))
    state.NOTES_DIR = tmp_path
    yield tmp_path
    config_mod._config = None
    state.NOTES_DIR = None


# --- note helpers -------------------------------------------------------

def test_slugify_keeps_only_first_line_and_strips_illegal_filename_chars():
    assert slugify("Headline\nignored second line") == "Headline"
    assert slugify('bad / \\ : * ? " < > | chars') == "bad          chars"


def test_create_note_raises_when_notes_dir_unset(offline, monkeypatch):
    state.NOTES_DIR = None
    with pytest.raises(RuntimeError, match="NOTES_DIR not set"):
        create_note("orphan thought")


def test_model_tag_for_note_from_ollama_title_default(tmp_path):
    from capture.core.config import load_config

    cfg = load_config(tmp_path / "missing.yaml")
    cfg["notes_dir"] = str(tmp_path)
    cfg["providers"]["title"]["default"] = "ollama_local"
    cfg["providers"]["title"]["ollama_local"]["model"] = "qwen-capable:latest"
    set_config(cfg)
    assert _model_tag_for_note() == "llm/qwen-capable"


def test_surface_serendipity_surfaces_an_old_note(tmp_path, monkeypatch):
    import capture.core.note as note_mod

    set_config(disabled_config(tmp_path))
    state.NOTES_DIR = tmp_path
    monkeypatch.setattr(note_mod, "metis_enabled", lambda: True)

    ancient = tmp_path / "20200101 - Ancient wisdom.md"
    ancient.write_text(
        "---\ntitle: Ancient wisdom\ndate: 2020-01-01\ntags: [kernel]\n---\n\nA line of old insight.\n"
    )
    os.utime(ancient, (1.0, 1.0))

    msg = surface_serendipity()
    assert msg is not None
    assert "Ancient wisdom" in msg
    assert "old insight" in msg


# --- vocabulary / whisper hints -----------------------------------------

def test_load_whisper_dictionary_reads_notes_dir_file(tmp_path):
    dict_path = tmp_path / "whisper-dictionary.yaml"
    dict_path.write_text(
        yaml.dump(
            {
                "prompt_vocab": {"crypto": ["Satoshi", "cypherpunk"]},
                "corrections": {"teh": "the"},
                "prompt_templates": {"crypto": "Crypto memo about {terms}."},
            }
        )
    )
    vocab, corrections, templates = load_whisper_dictionary(notes_dir=tmp_path)
    assert "crypto" in vocab
    assert "Satoshi" in vocab["crypto"]
    assert corrections["teh"] == "the"
    assert "Crypto memo" in templates["crypto"]


def test_build_whisper_prompt_includes_vocabulary_terms():
    vocab = {"general": ["alpha", "beta"], "philosophy": ["nous"]}
    templates = {"general": "Terms: {terms}."}
    prompt = build_whisper_prompt(vocab, templates, topic="philosophy")
    assert prompt is not None
    assert "alpha" in prompt
    assert "nous" in prompt


def test_apply_corrections_is_case_insensitive():
    assert apply_corrections("Teh Cypherpunk", {"teh": "the"}) == "the Cypherpunk"


def test_flatten_vocabulary_dedupes_across_topics():
    vocab = {"a": ["x", "y"], "b": ["y", "z"]}
    assert flatten_vocabulary(vocab) == ["x", "y", "z"]


# --- pipeline stubs with disabled providers -----------------------------

def test_transcribe_audio_returns_none_when_transcription_disabled(offline, tmp_path):
    wav = tmp_path / "silent.wav"
    wav.write_bytes(b"RIFF")
    assert transcribe_audio(wav) is None


def test_ocr_image_returns_none_when_ocr_disabled(offline, tmp_path):
    png = tmp_path / "page.png"
    png.write_bytes(b"\x89PNG")
    assert ocr_image(png) is None


# --- prompts ------------------------------------------------------------

def test_load_prompt_reads_bundled_title_template():
    text = load_prompt("title")
    assert "{content}" in text


def test_format_prompt_substitutes_kwargs():
    rendered = format_prompt("title", content="hello world")
    assert "hello world" in rendered


# --- config secrets -----------------------------------------------------

def test_resolve_secret_reads_environment(monkeypatch):
    monkeypatch.setenv("CAPTURE_TEST_SECRET", "s3cret")
    assert resolve_secret("env:CAPTURE_TEST_SECRET") == "s3cret"
    assert resolve_secret("plain-value") == "plain-value"


# --- connections keyword search -----------------------------------------

def test_keyword_connections_finds_notes_with_overlapping_keywords(offline):
    from capture.core.config import load_config

    cfg = load_config(offline / "missing.yaml")
    cfg["notes_dir"] = str(offline)
    cfg["providers"]["connections"]["default"] = "keyword"
    set_config(cfg)

    related = offline / "20250101 - Blockchain governance.md"
    related.write_text("---\ntitle: Blockchain governance\ntags: [kernel]\n---\n\ncryptography networks\n")

    provider = KeywordConnectionsProvider({}, cfg)
    hits = provider.find(
        "cryptography networks governance decentralization",
        notes_dir=offline,
        exclude=None,
    )
    assert "Blockchain governance" in hits


# --- ollama title parsing (HTTP mocked) ---------------------------------

def test_ollama_title_strips_title_prefix_from_model_output(monkeypatch):
    monkeypatch.setattr(
        "capture.providers.ollama_http.post_json",
        lambda *args, **kwargs: {"response": "Title: My distilled headline"},
    )
    provider = OllamaTitleProvider({"host": "http://127.0.0.1:11434", "model": "qwen-capable"})
    assert provider.generate("some long captured thought") == "My distilled headline"
