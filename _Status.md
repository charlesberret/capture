---
project: capture
kind: software
phase: active
canonical: ~/cloud/git-projects/capture
deps: pip
test_cmd: .venv/bin/pytest tests/ -q
test_signal: 37 passed
healthbeacon: none
---

## Status

Quick multi-modal note capture CLI — text, voice, images, PDFs, and an iOS staging
folder — producing timestamped markdown notes with LLM-generated titles and tags.
Refactored 2026-07-09 into a package with per-feature model providers; the iOS
SwiftUI app landed in the same pass.

Revived 2026-09-04 after months dormant. It had been unrunnable: the `bin/capture`
symlink on PATH was dangling (pointed at the pre-move `code/active/` path), and
`~/.config/capture/config.yaml` aimed `notes_dir` at an iCloud folder that no longer
exists. Both repointed at canonical paths (`~/cloud/sync/notes`). whisper + pyobjc
installed into `.venv`, so voice and Apple Vision OCR work again.

Same pass fixed the note contract: capture was emitting `tags: [[kernel]], [[captured]]`
— invalid YAML, and the exact format a 211-note migration (`notes/_review/tags-bracket-fix-ledger.csv`)
had been run to undo. It now writes `tags: [kernel, captured, llm/qwen]`, pinned by
`tests/test_note_contract.py`. `~/cloud/sync/code/bin/capture-reprocess` had the same
bug plus a parser that read migrated notes as untagged — it would have re-bracketed
all 211. Fixed too.

Also fixed: the Ollama warmup killed the model load it had started after 5s, so every
capture paid a cold start and blew the 20s title timeout, silently falling back to a
truncated title. A capture went 40s → 4.8s and now gets a real LLM title. And the
keyword connection finder matched each new note against itself, since `create_note`
writes the file before searching.

A 2026-09-05 reprocess pass over the notes root surfaced two more bugs in
`capture-reprocess`, both now fixed: `ollama run` leaks ANSI escapes into
captured stdout (one note's frontmatter was corrupted and restored from backup),
and the frontmatter updater only *replaced* `title:`/`tags:` lines, never
inserted them — so notes carrying only kind/subject/status/source were rewritten
unchanged after burning two LLM calls each. The sanitiser now lives in
`capture/core/text.py`, shared by the note writer and the ollama providers.

A third bug surfaced on the re-run: the script wrote `title: {model_output}`
unquoted, so a generated title containing a colon ("Artificial Metis: Beyond the
Turing Test") broke the block. Three notes were corrupted this way and repaired
in place. capture-reprocess now quotes scalars and, as a backstop, parses the
frontmatter it just built and refuses to write anything that does not load. Its
shebang moved to the fleet interpreter (`~/.venvs/fleet/bin/python3`), which has
PyYAML; system python3 does not.

Two further problems were content-level rather than syntactic. The script titled
from an *empty* body and got a confabulation — an empty note's human title
"Drake-Seti-Bateson" became "Avicenna's M3 Pro Configuration", the machine's own
hostname; there is now a `MIN_BODY_CHARS` guard. And `is_generic_title()` treated
any title under 20 characters as machine-generated, so "Ode to Hesse" and "Tools
to Think With" were replaced with flatter LLM titles. Length is not the signal:
the rule now tests whether the title is a prefix of the body, which is what
first-line truncation actually looks like. All three titles restored.

Final state: 88 root notes, 0 unparseable, 0 bodies altered, 0 human titles
overwritten, 81 enhanced. Root notes backed up to
`notes/_review/backup-root-notes-2026-09-05/` before the pass.

Added 2026-09-06: `capture fragments` — scans the notes root for bodies under
200 chars and files expansion items on a new Kettle desk at
`~/cloud/sync/notes/.kettle/`. Grew directly out of the reprocess pass: a note
too short to title honestly is also too short to be useful, and flagging it beats
confabulating metadata for it. Queue-only by design; notes are never modified. A
dismissal is recorded on the desk and survives every rescan, which is what makes
a length heuristic tolerable — the bar cannot distinguish a seed from a terse but
finished claim.

## Next action

- [ ] Decide whether capture should file into the staging folder or keep writing
      straight to the notes root (`notes-process` classifies either way)
- [ ] Work the 21 fragment items on `notes/.kettle/` — decide the real bar by
      dismissing the ones that are finished as written

## Known gaps

- Test suite covers the note contract only — config precedence, provider resolution,
  and the `process` folder walk are still untested
- No healthbeacon
- Deps declared in `pyproject.toml` only; no lock, so dep-freshness reads blind
- `notes/coursework/202601170656 - tibetan.md` holds a second frontmatter block inside
  its body (merge artifact, legacy bracket tags); top-level frontmatter is valid —
  flagged, not touched
- `ios/Capture.xcodeproj` is xcodegen-generated but tracked in git
