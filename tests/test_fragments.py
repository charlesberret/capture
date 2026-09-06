"""Fragment scanning and Kettle desk reconciliation.

The load-bearing property is that reconcile() never loses a human answer: a
fragment dismissed as "already complete" must stay dismissed across every later
scan, or the desk becomes noise and gets ignored.
"""

from __future__ import annotations

import json

import pytest

from capture.core import fragments as frag


def write_note(d, name, body, title=None):
    fm = f"title: {title}\n" if title else ""
    (d / name).write_text(f"---\n{fm}kind: atom\n---\n\n{body}\n")
    return d / name


@pytest.fixture
def notes(tmp_path):
    write_note(tmp_path, "202601010000 - seed.md",
               "A theme: writing on the body. Palm reading, tattoos, all physical markings.",
               title="Seed")
    write_note(tmp_path, "202601010001 - full.md", "x" * 500, title="Full")
    write_note(tmp_path, "202601010002 - empty.md", "", title="Empty")
    write_note(tmp_path, "_system_file.md", "short", title="System")
    (tmp_path / "CLAUDE.md").write_text("# docs\n")
    return tmp_path


# --- scanning ----------------------------------------------------------

def test_scan_finds_only_short_notes(notes):
    names = {f.path.name for f in frag.scan(notes)}
    assert names == {"202601010000 - seed.md", "202601010002 - empty.md"}


def test_scan_skips_underscore_files_and_docs(notes):
    names = {f.path.name for f in frag.scan(notes)}
    assert "_system_file.md" not in names and "CLAUDE.md" not in names


def test_threshold_is_honoured(notes):
    assert len(frag.scan(notes, threshold=10)) == 1     # only the empty one
    assert len(frag.scan(notes, threshold=1000)) == 3


def test_empty_note_is_distinguished_from_a_short_one(notes):
    by_name = {f.path.name: f for f in frag.scan(notes)}
    assert by_name["202601010002 - empty.md"].is_empty
    assert not by_name["202601010000 - seed.md"].is_empty


def test_entry_carries_the_fragment_text_so_the_desk_can_prompt(notes):
    f = next(f for f in frag.scan(notes) if not f.is_empty)
    entry = frag.to_entry(f, notes, 200)
    assert "writing on the body" in entry["brief"]
    assert entry["ask_type"] == "expansion"
    assert entry["status"] == "pending"


def test_empty_note_brief_warns_against_summarising_it(notes):
    f = next(f for f in frag.scan(notes) if f.is_empty)
    assert "invent" in frag.to_entry(f, notes, 200)["brief"]


# --- reconciliation: the part that must not lose answers ---------------

def test_new_fragments_are_added(notes):
    r = frag.reconcile(frag.load_queue(notes / "nope.json"), frag.scan(notes), notes, 200)
    assert len(r["added"]) == 2


def test_a_dismissed_fragment_is_never_refiled(notes):
    found = frag.scan(notes)
    q = frag.reconcile({"entries": []}, found, notes, 200)["queue"]
    # the user dismisses one as already complete
    for e in q["entries"]:
        if e["id"].endswith("seed"):
            e["status"] = "dismissed"
    again = frag.reconcile(q, found, notes, 200)
    assert again["added"] == []
    seed = next(e for e in again["queue"]["entries"] if e["id"].endswith("seed"))
    assert seed["status"] == "dismissed", "a settled answer must survive re-scanning"


def test_rescanning_does_not_duplicate_entries(notes):
    found = frag.scan(notes)
    q = frag.reconcile({"entries": []}, found, notes, 200)["queue"]
    q = frag.reconcile(q, found, notes, 200)["queue"]
    q = frag.reconcile(q, found, notes, 200)["queue"]
    ids = [e["id"] for e in q["entries"]]
    assert len(ids) == len(set(ids)) == 2


def test_a_note_that_grew_gets_resolved(notes):
    q = frag.reconcile({"entries": []}, frag.scan(notes), notes, 200)["queue"]
    (notes / "202601010000 - seed.md").write_text("---\nkind: atom\n---\n\n" + "y" * 600)
    r = frag.reconcile(q, frag.scan(notes), notes, 200)
    seed = next(e for e in r["queue"]["entries"] if e["id"].endswith("seed"))
    assert seed["status"] == "resolved"


def test_growth_does_not_reopen_a_dismissed_entry(notes):
    q = frag.reconcile({"entries": []}, frag.scan(notes), notes, 200)["queue"]
    for e in q["entries"]:
        e["status"] = "dismissed"
    (notes / "202601010000 - seed.md").write_text("---\nkind: atom\n---\n\n" + "y" * 600)
    r = frag.reconcile(q, frag.scan(notes), notes, 200)
    assert all(e["status"] == "dismissed" for e in r["queue"]["entries"])


def test_unrelated_desk_entries_are_left_alone(notes):
    q = {"entries": [{"id": "some-other-task", "status": "pending", "title": "Not ours"}]}
    r = frag.reconcile(q, frag.scan(notes), notes, 200)
    other = next(e for e in r["queue"]["entries"] if e["id"] == "some-other-task")
    assert other["status"] == "pending"


# --- writing -----------------------------------------------------------

def test_write_queue_is_valid_json_and_round_trips(notes, tmp_path):
    q = frag.reconcile({"entries": []}, frag.scan(notes), notes, 200)["queue"]
    path = tmp_path / "desk" / "runtime" / "queue.json"
    frag.write_queue(path, q)
    assert len(json.loads(path.read_text())["entries"]) == 2
