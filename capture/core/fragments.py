"""Find notes too short to be useful yet, and file them on the Kettle desk.

A captured thought often lands as a few words — enough to remember, not enough
to work from. This scans the notes root for those fragments and files an
expansion item per fragment on the tree's `.kettle/` desk.

Notes themselves are never modified: the frontmatter contract belongs to
notes-process, and a fragment is a fact about a note rather than a property of
it. That also means a dismissal has to live on the desk, which is what makes a
crude length test tolerable — say "this one is finished" once and it stays said.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Below this a note reads as a seed rather than a workable atom. Chosen against
# the real distribution: it catches bullet-list seeds while mostly sparing
# complete-but-terse claims, which land around 200-260 characters.
DEFAULT_THRESHOLD = 200

# An empty note is a different problem from a short one, and the only case where
# an LLM must not be asked to summarise — with nothing to read it confabulates,
# which is how one note's title became the hostname of the machine it sat on.
# "Empty" means empty: a 28-character thought is short, not absent.

# Statuses that mean "already answered" — never re-file these.
SETTLED = {"dismissed", "done", "resolved", "complete", "rejected"}

BRIEF_EXCERPT_CHARS = 400


@dataclass
class Fragment:
    path: Path
    title: str
    chars: int
    words: int
    excerpt: str

    @property
    def is_empty(self) -> bool:
        return self.chars == 0

    @property
    def entry_id(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.path.stem.lower()).strip("-")
        return f"expand-{slug}"[:80]


def split_note(text: str) -> tuple[str, str]:
    """Return (frontmatter, body). Both empty if there is no frontmatter."""
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    return parts[1], parts[2]


def note_title(frontmatter: str, path: Path) -> str:
    m = re.search(r"^title:\s*(.+)$", frontmatter, re.M)
    if m:
        return m.group(1).strip().strip('"').strip("'")
    stem = path.stem
    return stem.split(" - ", 1)[1] if " - " in stem else stem


def scan(notes_dir: Path, threshold: int = DEFAULT_THRESHOLD) -> list[Fragment]:
    """Find notes at the root of `notes_dir` whose body is under `threshold`."""
    out: list[Fragment] = []
    for path in sorted(notes_dir.glob("*.md")):
        if path.name.startswith(("_", ".")) or path.name == "CLAUDE.md":
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        frontmatter, body = split_note(text)
        body = body.strip()
        if len(body) >= threshold:
            continue
        out.append(
            Fragment(
                path=path,
                title=note_title(frontmatter, path),
                chars=len(body),
                words=len(body.split()),
                excerpt=body[:BRIEF_EXCERPT_CHARS],
            )
        )
    return out


def _brief(frag: Fragment, threshold: int) -> str:
    if frag.is_empty:
        return (
            f"This note has no body at all ({frag.chars} chars) — only frontmatter. "
            f"Either write the thought it was meant to hold, or delete it. "
            f"Do not ask a model to summarise it; with nothing to read it will invent "
            f"something plausible."
        )
    return (
        f"{frag.chars} chars / {frag.words} words — under the {threshold}-char bar "
        f"for a workable atom. Expand it into something you could draw on later, or "
        f"dismiss it if it is already complete as written.\n\n"
        f"Current text:\n{frag.excerpt}"
    )


def to_entry(frag: Fragment, notes_dir: Path, threshold: int) -> dict:
    """Build a Kettle queue entry in the schema the other desks use."""
    return {
        "id": frag.entry_id,
        "title": f"Expand: {frag.title}",
        "path": str(frag.path),
        "project": "Notes",
        "project_root": str(notes_dir),
        "ask_type": "expansion",
        "ask": (
            "Write the thought out, or delete the note."
            if frag.is_empty
            else "Expand this fragment into a workable atom, or dismiss it as complete."
        ),
        "desk_item": None,
        "urgency": "normal" if frag.is_empty else "low",
        "status": "pending",
        "unblocks": "Using this note as a source in writing projects",
        "brief": _brief(frag, threshold),
    }


def desk_path(notes_dir: Path) -> Path:
    return notes_dir / ".kettle" / "runtime" / "queue.json"


def load_queue(path: Path) -> dict:
    if not path.exists():
        return {"curated": "empty — entries are filed by curating agents", "entries": []}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"curated": "empty — entries are filed by curating agents", "entries": []}
    data.setdefault("entries", [])
    return data


def reconcile(queue: dict, fragments: list[Fragment], notes_dir: Path, threshold: int) -> dict:
    """Merge a scan into an existing queue without losing human answers.

    Three rules, in order of importance:
      1. An entry the user has settled is never re-filed and never reopened.
      2. A pending entry whose note has since grown past the bar is resolved.
      3. Anything genuinely new is appended.
    """
    entries = list(queue.get("entries", []))
    by_id = {e.get("id"): e for e in entries if e.get("id")}
    found = {f.entry_id: f for f in fragments}

    added, resolved, skipped = [], [], []

    for frag in fragments:
        existing = by_id.get(frag.entry_id)
        if existing is None:
            entry = to_entry(frag, notes_dir, threshold)
            entries.append(entry)
            by_id[frag.entry_id] = entry
            added.append(frag.entry_id)
        elif str(existing.get("status", "")).lower() in SETTLED:
            skipped.append(frag.entry_id)   # answered already; leave it answered

    for entry in entries:
        eid = entry.get("id", "")
        if not eid.startswith("expand-"):
            continue
        status = str(entry.get("status", "")).lower()
        if status == "pending" and eid not in found:
            entry["status"] = "resolved"
            entry["resolved_note"] = "note grew past the fragment threshold"
            resolved.append(eid)

    queue["entries"] = entries
    queue["curated"] = f"{datetime.now().strftime('%Y-%m-%d')} capture fragments"
    return {"added": added, "resolved": resolved, "skipped": skipped, "queue": queue}


def write_queue(path: Path, queue: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)
