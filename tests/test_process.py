"""Legacy `process` folder walk: staging files become notes; notes dir is tmp."""

from __future__ import annotations

from capture.core import state
from capture.core.config import set_config
from capture.core.pipeline import process_capture_folder
from tests.test_capture_floor import disabled_config


def test_process_writes_text_and_deletes_the_staging_file(tmp_path, capsys):
    import capture.core.config as config_mod

    notes = tmp_path / "notes"
    staging = tmp_path / "staging"
    notes.mkdir()
    staging.mkdir()
    (staging / "idea.txt").write_text("a short captured thought\n")
    (staging / "README.md").write_text("leave me\n")
    (staging / ".DS_Store").write_text("junk")

    cfg = disabled_config(notes)
    cfg["capture_dir"] = str(staging)
    set_config(cfg)
    state.NOTES_DIR = notes
    try:
        process_capture_folder()
    finally:
        config_mod._config = None
        state.NOTES_DIR = None

    written = list(notes.glob("*.md"))
    assert len(written) == 1
    assert "a short captured thought" in written[0].read_text()
    assert not (staging / "idea.txt").exists()
    assert (staging / "README.md").exists()


def test_process_missing_folder_is_a_no_op(tmp_path, capsys):
    import capture.core.config as config_mod

    notes = tmp_path / "notes"
    notes.mkdir()
    cfg = disabled_config(notes)
    cfg["capture_dir"] = str(tmp_path / "no-such-staging")
    set_config(cfg)
    state.NOTES_DIR = notes
    try:
        process_capture_folder()
    finally:
        config_mod._config = None
        state.NOTES_DIR = None

    assert list(notes.glob("*.md")) == []
    assert "Capture folder not found" in capsys.readouterr().out


def test_process_skips_unknown_suffix_and_leaves_the_file(tmp_path):
    import capture.core.config as config_mod

    notes = tmp_path / "notes"
    staging = tmp_path / "staging"
    notes.mkdir()
    staging.mkdir()
    leftover = staging / "notes.zip"
    leftover.write_bytes(b"PK")

    cfg = disabled_config(notes)
    cfg["capture_dir"] = str(staging)
    set_config(cfg)
    state.NOTES_DIR = notes
    try:
        process_capture_folder()
    finally:
        config_mod._config = None
        state.NOTES_DIR = None

    assert leftover.exists()
    assert list(notes.glob("*.md")) == []
