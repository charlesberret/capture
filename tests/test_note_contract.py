"""The note frontmatter contract.

Capture writes into `~/cloud/sync/notes/`, whose frontmatter is consumed by
machines (notes-process, Obsidian, gbrain). In 2026 a 211-note migration had
to undo `tags: [[kernel]], [[captured]]` — invalid YAML — into the flow
sequence `tags: [kernel, captured]`. Capture was the source of that format and
kept emitting it. These tests pin the contract so it cannot regress again.
"""

from __future__ import annotations

import yaml
import pytest

from capture.core import note as note_mod
from capture.core.note import create_note, format_tags, normalize_tag, yaml_scalar


def frontmatter_of(path):
    text = path.read_text()
    assert text.startswith("---\n"), "note must open with a frontmatter block"
    return yaml.safe_load(text.split("---", 2)[1])


# --- tag normalisation -------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("kernel", "kernel"),
        ("[[kernel]]", "kernel"),          # legacy wikilink form
        ("[[llm:phi3]]", "llm/phi3"),      # legacy model tag
        ("llm:qwen-capable", "llm/qwen-capable"),
        ("  spaced  ", "spaced"),
        ("", None),
    ],
)
def test_normalize_tag(raw, expected):
    assert normalize_tag(raw) == expected


def test_format_tags_is_a_yaml_flow_sequence():
    assert format_tags(["kernel", "captured"]) == "[kernel, captured]"


def test_format_tags_dedupes_and_strips_sequence_breakers():
    # a comma or bracket inside a tag would split/short the flow sequence
    assert format_tags(["a", "a", "b,c", "[d]"]) == "[a, bc, d]"


def test_format_tags_output_parses_as_a_list():
    line = f"tags: {format_tags(['[[kernel]]', '[[captured]]', '[[llm:phi3]]'])}"
    assert yaml.safe_load(line)["tags"] == ["kernel", "captured", "llm/phi3"]


# --- scalar quoting ----------------------------------------------------

@pytest.mark.parametrize("title", ["plain title", "[draft] thing", "yes", "has: colon", "ends:", "- dashed"])
def test_yaml_scalar_survives_a_round_trip(title):
    assert yaml.safe_load(f"title: {yaml_scalar(title)}")["title"] == title


# --- the whole note ----------------------------------------------------

@pytest.fixture
def notes_dir(tmp_path, monkeypatch):
    """A capture configured with no LLM in the loop, writing to tmp_path."""
    monkeypatch.setattr(note_mod.state, "NOTES_DIR", tmp_path)
    monkeypatch.setattr(note_mod, "generate_title", lambda content, warmup=None: "A Test Note")
    monkeypatch.setattr(note_mod, "suggest_tags", lambda content, warmup=None: ["alpha", "beta"])
    monkeypatch.setattr(note_mod, "find_connections", lambda content, exclude=None: [])
    monkeypatch.setattr(note_mod, "surface_serendipity", lambda: None)
    monkeypatch.setattr(note_mod, "_model_tag_for_note", lambda: "llm/qwen-capable")
    return tmp_path


def test_created_note_frontmatter_parses(notes_dir):
    fm = frontmatter_of(create_note("some captured thought"))
    assert isinstance(fm["tags"], list)
    assert fm["title"] == "A Test Note"


def test_created_note_carries_base_and_suggested_tags(notes_dir):
    fm = frontmatter_of(create_note("some captured thought"))
    assert fm["tags"] == ["kernel", "captured", "llm/qwen-capable", "alpha", "beta"]


def test_no_tag_uses_the_legacy_bracket_form(notes_dir):
    """The exact defect the 211-note migration had to undo."""
    text = create_note("some captured thought").read_text()
    tags_line = next(l for l in text.splitlines() if l.startswith("tags:"))
    assert "[[" not in tags_line


def test_awkward_title_still_yields_valid_frontmatter(notes_dir, monkeypatch):
    """A title full of YAML metacharacters must still round-trip intact."""
    awkward = "[draft]: yes, or no"
    monkeypatch.setattr(note_mod, "generate_title", lambda content, warmup=None: awkward)
    fm = frontmatter_of(create_note("some captured thought"))
    assert fm["title"] == awkward


def test_connections_never_match_the_note_just_written(notes_dir, monkeypatch):
    """create_note writes the file before searching, so it is its own best match."""
    from capture.providers.connections.keyword import KeywordConnectionsProvider

    monkeypatch.setattr(note_mod, "metis_enabled", lambda: True)
    provider = KeywordConnectionsProvider({}, {"metis": {"max_keywords": 10, "max_connections": 3}})
    written = create_note("cypherpunk cryptography infrastructure surveillance")
    found = provider.find(
        "cypherpunk cryptography infrastructure surveillance",
        notes_dir=notes_dir,
        exclude=written,
    )
    assert written.stem.split(" - ", 1)[-1] not in found


# --- model output sanitising -------------------------------------------

def test_normalize_tag_drops_ansi_escapes():
    """A stray escape from `ollama run` made one real note unparseable."""
    assert normalize_tag("publication mo\x1b[2D\x1b[K") == "publication mo"


def test_clean_model_output_strips_spinner_noise():
    from capture.core.text import clean_model_output

    assert clean_model_output("\x1b[?25l⠙ \x1b[K\x1b[?25hA Real Title") == "⠙ A Real Title"
    assert "\x1b" not in clean_model_output("a\x1b[2Db")


def test_frontmatter_survives_a_tag_full_of_escapes():
    line = f"tags: {format_tags(['kernel', 'publication mo\x1b[2D\x1b[K', 'ok'])}"
    assert yaml.safe_load(line)["tags"] == ["kernel", "publication mo", "ok"]
