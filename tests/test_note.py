from __future__ import annotations

from datetime import datetime

import yaml

from capture.core import note


class FixedDateTime:
    @classmethod
    def now(cls):
        return datetime(2026, 9, 15, 12, 34)


def test_create_note_filename_frontmatter_and_body(
    disabled_provider_config, monkeypatch, tmp_path
):
    monkeypatch.setattr(note, "datetime", FixedDateTime)
    body = "A deterministic test note\nwith a second line."

    path = note.create_note(body)

    assert path == tmp_path / "202609151234 - A deterministic test note.md"
    _, frontmatter, saved_body = path.read_text().split("---", 2)
    assert yaml.safe_load(frontmatter) == {
        "title": "A deterministic test note",
        "date": "2026-09-15 12:34",
        "tags": ["[[kernel]]", "[[captured]]"],
    }
    assert saved_body.lstrip("\n") == f"{body}\n"
