"""Pin the five capture-reprocess corruption modes (the 2026-09-05 incident).

capture-reprocess is a script, not package code; these tests load it as a
module and drive its real frontmatter write path against tmp_path notes —
offline, with `ollama run` stubbed at subprocess. Skipped when the script
is not present (it is not part of the public package).
"""

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

# The script is not part of this package. Point CAPTURE_REPROCESS at it, or
# have `capture-reprocess` on PATH. Otherwise these tests skip.
_found = os.environ.get("CAPTURE_REPROCESS") or shutil.which("capture-reprocess")
SCRIPT = Path(_found) if _found else Path()

pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(),
    reason="capture-reprocess not on PATH and CAPTURE_REPROCESS unset",
)

BODY = (
    "A longer body with enough text for the model to work from honestly. "
    "It discusses entropy, key length, and the politics of interception."
)


@pytest.fixture()
def rp():
    loader = importlib.machinery.SourceFileLoader("capture_reprocess", str(SCRIPT))
    spec = importlib.util.spec_from_file_location("capture_reprocess", SCRIPT, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_note(tmp_path, fm_lines, body=BODY, name="202601011200 - n.md"):
    p = tmp_path / name
    p.write_text("---\n" + "\n".join(fm_lines) + "\n---\n\n" + body)
    return p


def stub_ollama(rp, monkeypatch, title="Tidy Title", tags="alpha, beta, gamma"):
    def fake_run(cmd, **kw):
        prompt = cmd[-1]
        out = title if "concise 3-8 word" in prompt else tags
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(rp.subprocess, "run", fake_run)


def fm_of(path):
    return path.read_text().split("---\n", 2)[1]


# 1. `ollama run` leaks ANSI escapes into captured stdout; they must never
#    reach frontmatter (they corrupted a note on the pass).
def test_ansi_escapes_never_reach_frontmatter(rp, monkeypatch, tmp_path):
    stub_ollama(rp, monkeypatch, title="Tidy Title\x1b[2K\x1b[2D")
    note = write_note(tmp_path, ["title: A longer body with enough", "tags: [kernel, captured]"])
    assert rp.enhance_note(note)
    assert "\x1b" not in note.read_text()


# 2. A frontmatter with only kind/subject/status/source must gain title: and
#    tags: lines — the old loop replaced lines, never inserted them.
def test_missing_title_and_tags_keys_are_inserted(rp, monkeypatch, tmp_path):
    stub_ollama(rp, monkeypatch)
    note = write_note(tmp_path, ["kind: atom", "subject: crypto", "status: live", "source: book"])
    assert rp.enhance_note(note)
    fm = fm_of(note)
    assert "title: Tidy Title" in fm
    assert "tags: [" in fm


# 3. A model title containing a colon must be quoted, else the block breaks
#    ("Artificial Metis: Beyond the Turing Test" corrupted three notes).
def test_colon_title_is_quoted_and_parses(rp, monkeypatch, tmp_path):
    stub_ollama(rp, monkeypatch, title="Artificial Metis: Beyond the Turing Test")
    note = write_note(tmp_path, ["title: A longer body with enough", "tags: [kernel, captured]"])
    assert rp.enhance_note(note)
    fm = fm_of(note)
    assert 'title: "Artificial Metis: Beyond the Turing Test"' in fm
    assert rp.frontmatter_is_valid(fm)


# 4. A body under MIN_BODY_CHARS gets no generated title at all — an empty
#    note once had its human title confabulated away.
def test_short_body_is_left_untouched(rp, monkeypatch, tmp_path):
    stub_ollama(rp, monkeypatch)
    note = write_note(
        tmp_path, ["title: Drake-Seti-Bateson", "tags: [kernel]"], body="too short"
    )
    before = note.read_text()
    assert not rp.enhance_note(note)
    assert note.read_text() == before


# 5. A human title that is not a prefix of the body must survive — length is
#    not the signal ("Ode to Hesse" was wrongly replaced once).
def test_human_title_not_a_body_prefix_survives(rp, monkeypatch, tmp_path):
    stub_ollama(rp, monkeypatch, title="Flatter Model Title")
    note = write_note(tmp_path, ["title: Ode to Hesse", "tags: [kernel, captured]"])
    assert rp.enhance_note(note)
    assert "title: Ode to Hesse" in fm_of(note)
