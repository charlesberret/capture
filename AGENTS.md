# AGENTS.md — capture

Guidance for any coding agent working in this repository. This file is about
this tree only.

## What this is

`capture` is a small Python CLI (plus a native SwiftUI app in `ios/`) that
turns text, voice, photos, and PDFs into timestamped markdown notes with YAML
frontmatter. The notes are consumed by other tools downstream, so the
**note file contract is load-bearing**: changes to what a note looks like
break machines elsewhere, not just this repo.

## The note contract (do not break)

- Filename: `YYYYMMDDHHMM - Slug.md` at the root of the notes directory
  (timestamp, space, dash, space, slugified first line; timestamp-only name
  when the slug is empty).
- Frontmatter opens with `---`, is valid YAML, and carries `title`, `date`
  (`YYYY-MM-DD HH:MM`), and `tags`.
- `tags` is a YAML flow sequence (`[kernel, captured]`) — never `[[wikilinks]]`,
  and never anything a comma or bracket could split. Use
  `capture.core.note.format_tags` / `normalize_tag` rather than formatting by
  hand.
- Scalar values go through `capture.core.note.yaml_scalar` so titles with
  colons or YAML metacharacters survive a round trip.
- The body after the frontmatter is the captured content, verbatim.

`tests/test_note_contract.py` and `tests/test_capture_floor.py` pin all of
this. Run the suite before and after anything that writes a note:

```bash
.venv/bin/python -m pytest tests/ -q
```

## Running and testing offline

The test suite must stay green with **no Ollama, no Gemini, and no network**.
Every pipeline stage has a `disabled` backend (title also has `truncate`);
tests inject a config with all stages disabled and drive the real provider
registry (`tests/test_capture_floor.py`). Keep it that way: if a test would
need a live model, the test is wrong, not the environment. Do not "fix" a
failing suite by pointing tests at a real endpoint.

## Layout

```
capture/
├── cli.py                 # CLI entry point
├── core/
│   ├── config.py          # Config load + set_config; per-stage provider defaults
│   ├── pipeline.py        # capture_quick/text/voice/photo/process flows
│   ├── note.py            # the note contract — filename, frontmatter, tags
│   ├── fragments.py       # short-note scanning + Kettle desk queue
│   └── state.py           # NOTES_DIR, set by the CLI at startup
├── providers/
│   ├── registry.py        # resolve stage → backend from config
│   └── <stage>/           # one module per backend, incl. disabled
└── platforms/             # mac / ios provider default tables
ios/                       # SwiftUI app; writes the same note shape
tests/                     # pytest; offline by construction
```

Config resolution order: environment (`CAPTURE_CONFIG`, `OLLAMA_MODEL`,
`EDITOR`, `CAPTURE_METIS`) → config file → built-in defaults. The legacy
`llm:` block is merged into `providers:`; keep both paths working if you
touch config.

## Boundaries

- **One tree.** Work happens in this repository. Do not write to sibling
  repositories, do not dump Allsorts or Commonplace material here, and do not
  reorganize the notes directory this tool writes into.
- **No secrets.** API keys are referenced as `env:VAR_NAME` in config and stay
  in the environment or Keychain. Never hardcode one, never copy one into a
  test fixture or a note.
- **No publishing.** Do not run `gh repo create` or add remotes; pushes are a
  human decision.
- **Notes are data, not source.** The tool writes into the user's notes
  directory; tests must write into `tmp_path` only. Never touch real notes in
  a test or a script.
- The `kind` / `subject` / `status` / `source` frontmatter fields belong to a
  separate classification pass — capture deliberately does not stamp them.
- `capture fragments` files entries on the Kettle desk
  (`.kettle/runtime/queue.json`) and must never modify the notes themselves.

## Conventions

- Python 3.9+; the package has **no required dependencies** — PyYAML and the
  pyobjc packages are optional extras and everything degrades gracefully
  without them. Keep import-time optional.
- Providers are small classes resolved by `capture.providers.registry`; add a
  new backend as a new module under its stage, never an `if` in the caller.
- Tests live in `tests/`, one module per behavior, no network, no real notes
  directory.
