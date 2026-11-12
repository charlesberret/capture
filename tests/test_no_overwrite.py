"""Same-minute capture must not silently overwrite an existing note (strict xfails).

`create_note` names files from the current minute and the slugified first line; a
second write in that minute with the same headline targets the same path today.
Legacy `process` can file two staging text files that share a first line in one
pass and leave only the last body on disk. These tests assert the desired
behavior until the writer grows collision handling.
"""

from __future__ import annotations

import pytest

from capture.core import state
from capture.core.config import set_config
from capture.core.note import create_note
from capture.core.pipeline import process_capture_folder
from tests.test_capture_floor import disabled_config

FROZEN_MINUTE = "202611120148"
SHARED_HEADLINE = "Shared headline for collision test"


@pytest.fixture
def offline(tmp_path):
    import capture.core.config as config_mod

    set_config(disabled_config(tmp_path))
    state.NOTES_DIR = tmp_path
    yield tmp_path
    config_mod._config = None
    state.NOTES_DIR = None


@pytest.mark.xfail(
    strict=True,
    reason="create_note overwrites when filename collides in the same minute",
)
def test_create_note_twice_same_minute_preserves_both_bodies(offline, monkeypatch):
    monkeypatch.setattr("capture.core.note.timestamp", lambda: FROZEN_MINUTE)

    create_note(f"{SHARED_HEADLINE}\nfirst body")
    create_note(f"{SHARED_HEADLINE}\nsecond body")

    notes = sorted(offline.glob("*.md"))
    assert len(notes) == 2
    joined = "\n".join(path.read_text() for path in notes)
    assert "first body" in joined
    assert "second body" in joined


@pytest.mark.xfail(
    strict=True,
    reason="process can file two staging captures into one same-minute note",
)
def test_process_two_text_files_same_headline_same_minute_keeps_both(tmp_path, monkeypatch):
    import capture.core.config as config_mod

    notes = tmp_path / "notes"
    staging = tmp_path / "staging"
    notes.mkdir()
    staging.mkdir()
    (staging / "a-first.txt").write_text(f"{SHARED_HEADLINE}\nfrom staging a")
    (staging / "b-second.txt").write_text(f"{SHARED_HEADLINE}\nfrom staging b")

    cfg = disabled_config(notes)
    cfg["capture_dir"] = str(staging)
    set_config(cfg)
    state.NOTES_DIR = notes
    monkeypatch.setattr("capture.core.note.timestamp", lambda: FROZEN_MINUTE)

    try:
        process_capture_folder()
    finally:
        config_mod._config = None
        state.NOTES_DIR = None

    written = sorted(notes.glob("*.md"))
    assert len(written) == 2
    joined = "\n".join(path.read_text() for path in written)
    assert "from staging a" in joined
    assert "from staging b" in joined
