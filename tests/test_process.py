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


def _run_process(tmp_path, files):
    """Stage `files` (name → str|bytes), run the walk, return (notes, staging)."""
    import capture.core.config as config_mod

    notes = tmp_path / "notes"
    staging = tmp_path / "staging"
    notes.mkdir()
    staging.mkdir()
    for name, payload in files.items():
        path = staging / name
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(payload)

    cfg = disabled_config(notes)
    cfg["capture_dir"] = str(staging)
    set_config(cfg)
    state.NOTES_DIR = notes
    try:
        process_capture_folder()
    finally:
        config_mod._config = None
        state.NOTES_DIR = None
    return notes, staging


def test_process_unlinks_only_after_a_successful_write(tmp_path, monkeypatch):
    """Empty text, failed OCR, failed transcription, and failed PDF stay on disk.

    PDF OCR is hardcoded to Apple Vision (not the registry), so the test
    stubs that one call to None — the walk still owns the unlink decision.
    """
    monkeypatch.setattr("capture.core.pipeline.ocr_pdf", lambda path: None)

    notes, staging = _run_process(
        tmp_path,
        {
            "empty.txt": "   \n",
            "shot.jpg": b"\xff\xd8\xff",
            "scan.pdf": b"%PDF-not-a-real-document",
            "clip.wav": b"RIFF",
            "ok.txt": "a thought that should file\n",
        },
    )

    written = list(notes.glob("*.md"))
    assert len(written) == 1
    assert "a thought that should file" in written[0].read_text()
    assert not (staging / "ok.txt").exists()
    assert (staging / "empty.txt").exists()
    assert (staging / "shot.jpg").exists()
    assert (staging / "scan.pdf").exists()
    assert (staging / "clip.wav").exists()


def test_process_leaves_voice_file_when_transcribe_raises(tmp_path, monkeypatch):
    def boom(path, topic="general", correct=True):
        raise RuntimeError("whisper exploded")

    monkeypatch.setattr("capture.core.pipeline.transcribe_audio", boom)
    notes, staging = _run_process(tmp_path, {"clip.wav": b"RIFF"})

    assert (staging / "clip.wav").exists()
    assert list(notes.glob("*.md")) == []
