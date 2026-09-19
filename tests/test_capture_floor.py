"""The capture floor (LAB-236): the whole capture path with every model
provider **disabled** — no Ollama, no Gemini, no network — and the note
file contract pinned end to end: filename, frontmatter, body.

These tests deliberately refuse to stub at the function level. They inject a
config whose every stage resolves to a `disabled` (or no-LLM `truncate`)
backend and drive `create_note` / `capture_quick` through the real provider
registry. If a future default re-points a stage at a live model, the
`test_offline_stack_resolves_to_disabled_providers` assertions fail loudly
instead of silently phoning a model from inside the test suite.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from capture.core import state
from capture.core.config import set_config
from capture.core.note import create_note
from capture.core.pipeline import capture_quick
from capture.providers.registry import get_provider

FILENAME_RE = re.compile(r"^(?P<ts>\d{12}) - (?P<slug>.+)\.md$")


def disabled_config(notes_dir: Path) -> dict:
    """A complete config with every stage offline: disabled / truncate only."""
    return {
        "notes_dir": str(notes_dir),
        "capture_dir": str(notes_dir / "_capture-staging"),
        "whisper_dictionary": None,
        "editor": "nano",
        "llm": {
            "model": "qwen-capable",
            "enable_metis": True,
            "title_timeout": 60,
            "tag_timeout": 45,
            "content_threshold": 30,
            "whisper_model": "medium",
            "whisper_backend": "python",
            "auto_correct": True,
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
            "title": {"default": "disabled", "disabled": {}, "truncate": {}},
            "tags": {"default": "disabled", "disabled": {}},
            "correction": {"default": "disabled", "disabled": {}},
            "connections": {"default": "disabled", "disabled": {}},
        },
    }


@pytest.fixture
def offline(tmp_path):
    """Notes land in tmp_path with every provider disabled; nothing leaks."""
    import capture.core.config as config_mod

    set_config(disabled_config(tmp_path))
    state.NOTES_DIR = tmp_path
    yield tmp_path
    config_mod._config = None
    state.NOTES_DIR = None


# --- the offline stack itself -----------------------------------------

def test_offline_stack_resolves_to_disabled_providers(offline):
    from capture.providers.connections.disabled import DisabledConnectionsProvider
    from capture.providers.enrich.disabled import DisabledTagsProvider
    from capture.providers.enrich.truncate import TruncateTitleProvider
    from capture.providers.ocr.disabled import DisabledOCRProvider
    from capture.providers.refine.disabled import DisabledCorrectionProvider
    from capture.providers.transcription.disabled import DisabledTranscriptionProvider

    assert isinstance(get_provider("title"), TruncateTitleProvider)
    assert isinstance(get_provider("tags"), DisabledTagsProvider)
    assert isinstance(get_provider("correction"), DisabledCorrectionProvider)
    assert isinstance(get_provider("transcription"), DisabledTranscriptionProvider)
    assert isinstance(get_provider("ocr"), DisabledOCRProvider)
    assert isinstance(get_provider("connections"), DisabledConnectionsProvider)


def test_disabled_transcription_and_ocr_return_none_without_touching_the_file(
    offline,
):
    assert get_provider("transcription").transcribe(Path("nonexistent.wav"), hints={}) is None
    assert get_provider("ocr").extract(Path("nonexistent.png")) is None


# --- the filename contract --------------------------------------------

def test_note_filename_is_timestamp_space_dash_space_slug(offline):
    path = create_note("The Cypherpunk Mailing List as Unauthorized Workshop")
    m = FILENAME_RE.match(path.name)
    assert m, f"filename must be 'YYYYMMDDHHMM - Slug.md', got {path.name!r}"
    # the 12 digits are a real minute stamp, not an arbitrary number
    datetime.strptime(m.group("ts"), "%Y%m%d%H%M")


def test_filename_slug_matches_the_frontmatter_title(offline):
    path = create_note("A thought about capture tooling")
    m = FILENAME_RE.match(path.name)
    frontmatter = yaml.safe_load(path.read_text().split("---", 2)[1])
    assert m.group("slug") == frontmatter["title"]


def test_filename_strips_path_illegal_characters(offline):
    path = create_note(' ideas: the "best" *draft? ')
    assert not set(path.name) & set('/:*?"<>|')


def test_long_first_line_is_truncated_to_a_sane_filename(offline):
    long_line = "word " * 40  # 200 chars, far past the 50-char slug cap
    path = create_note(long_line)
    m = FILENAME_RE.match(path.name)
    assert len(m.group("slug")) <= 50


def test_empty_content_falls_back_to_timestamp_only(offline):
    path = create_note("")
    assert re.match(r"^\d{12}\.md$", path.name), path.name
    frontmatter = yaml.safe_load(path.read_text().split("---", 2)[1])
    assert frontmatter["title"] == "Untitled capture"


# --- frontmatter fields ------------------------------------------------

def test_frontmatter_carries_title_date_and_tags(offline):
    frontmatter = yaml.safe_load(create_note("some captured thought").read_text().split("---", 2)[1])
    assert set(frontmatter) == {"title", "date", "tags"}
    datetime.strptime(frontmatter["date"], "%Y-%m-%d %H:%M")


def test_offline_notes_carry_only_base_tags(offline):
    """With tags disabled, no model tag and no suggested tags may appear."""
    frontmatter = yaml.safe_load(create_note("some captured thought").read_text().split("---", 2)[1])
    assert frontmatter["tags"] == ["kernel", "captured"]


# --- the body -----------------------------------------------------------

def test_body_is_preserved_verbatim_after_the_frontmatter(offline):
    content = "first line\n\n## a markdown body\n\nwith trailing whitespace  "
    text = create_note(content).read_text()
    assert text.split("---", 2)[2] == f"\n\n{content}\n"


def test_multiline_body_lands_in_the_file_not_the_filename(offline):
    path = create_note("headline line\nsecond line that must not reach the slug")
    m = FILENAME_RE.match(path.name)
    assert "second line" not in m.group("slug")
    assert "second line that must not reach the slug" in path.read_text()


# --- the full pipeline, end to end, offline ------------------------------

def test_capture_quick_writes_a_contract_note_with_every_provider_disabled(offline):
    path = capture_quick("an idea worth keeping exactly as typed")
    assert path.exists()

    text = path.read_text()
    frontmatter = yaml.safe_load(text.split("---", 2)[1])
    assert frontmatter["tags"] == ["kernel", "captured"]
    datetime.strptime(frontmatter["date"], "%Y-%m-%d %H:%M")
    assert FILENAME_RE.match(path.name)
    assert "an idea worth keeping exactly as typed" in text
