# capture

Quick multi-modal note capture with LLM-powered titles and tags.

Two surfaces, one note shape:

- **Mac CLI** — `capture quick "idea"` (text, editor, voice, photo) writes
  timestamped markdown notes with YAML frontmatter.
- **Native iOS app** (`ios/`) — the phone path: photograph a page, **see the
  OCR**, **highlight the span** that matters, the agent proposes title + tags,
  **you confirm** (edit allowed) and may add a short memo — only then is the
  same `.md` note written. Nothing auto-saves.

An older iOS-Shortcuts staging flow still works but is **legacy** (see
[iOS Shortcuts (legacy)](#ios-shortcuts-legacy)); the native app is the
product path.

## Install

```bash
# Option 1: pipx (recommended)
pipx install .

# Option 2: pip editable, into a venv
python3 -m venv .venv && .venv/bin/pip install -e '.[all]'

# Option 3: symlink the installed entry point onto your PATH
ln -s "$PWD/.venv/bin/capture" ~/.local/bin/capture
```

Note that `capture/` is the Python package, not a runnable script — symlink the
generated `bin/capture` entry point, never `capture/capture`.

### Dependencies

**Required:** Python 3.9+

**Optional:**
- [Ollama](https://ollama.com) + a model (e.g. `ollama pull qwen2.5:7b`; set any custom model with `OLLAMA_MODEL`) -- smart titles and tags
- [Whisper](https://github.com/openai/whisper) -- voice transcription
- [PyObjC](https://pyobjc.readthedocs.io/) -- Apple Vision OCR (macOS only)
- [tesseract](https://github.com/tesseract-ocr/tesseract) -- OCR fallback
- [fzf](https://github.com/junegunn/fzf) -- interactive destination picker
- [SoX](https://sox.sourceforge.net/) (`rec`) or ffmpeg -- voice recording
- [PyYAML](https://pyyaml.org/) -- config file support

Without Ollama, titles fall back to first-line truncation and tags are skipped. Without PyYAML, built-in defaults are used. Everything degrades gracefully.

## Usage

```bash
capture                    # Interactive menu
capture quick "idea"       # One-liner capture
capture text               # Open editor for longer text
capture photo image.jpg    # OCR from image
capture voice              # Record and transcribe
capture voice --multi      # Record multiple notes with pipelined transcription
capture process            # Legacy: process the iOS-Shortcuts staging folder
capture fragments          # Find notes too short to be useful yet
```

### Options

```
--dest, -d PATH       Save notes to a specific directory
--config PATH         Use a specific config file
--init-config         Generate default config at ~/.config/capture/config.yaml
```

## Configuration

Capture works out of the box with no config file. To customize:

```bash
capture --init-config     # Creates ~/.config/capture/config.yaml
```

Or copy `config.example.yaml` to `~/.config/capture/config.yaml` and edit.

### Per-feature providers

Each pipeline stage picks its own backend — local models, cloud APIs, or `disabled`:

| Stage | Mac default | iOS default (native app) |
|-------|-------------|---------------------------|
| `transcription` | `whisper_local` | `gemini_flash` |
| `ocr` | `apple_vision` | `apple_vision` |
| `title` | `ollama_local` | `gemini_flash` |
| `tags` | `ollama_local` | `gemini_flash` |
| `correction` | `ollama_local` | `disabled` |
| `connections` | `keyword` | `keyword` |

Available backends per stage:

- **transcription:** `whisper_local`, `gemini_flash`, `disabled`
- **ocr:** `apple_vision`, `tesseract`, `disabled`
- **title:** `ollama_local`, `gemini_flash`, `truncate`, `disabled`
- **tags:** `ollama_local`, `gemini_flash`, `disabled`
- **correction:** `ollama_local`, `gemini_flash`, `claude`, `disabled`

API keys use `env:VAR_NAME` in config (e.g. `api_key: env:GOOGLE_API_KEY`).
The CLI never needs one: with every stage `disabled` it still writes correct
notes (see `tests/test_capture_floor.py`).

The legacy `llm:` config block is still honored and merged into provider settings.

### Config precedence

1. Environment variables (`OLLAMA_MODEL`, `EDITOR`, `CAPTURE_METIS`)
2. Config file (`$CAPTURE_CONFIG` env var, or `~/.config/capture/config.yaml`)
3. Built-in defaults

### Config schema

See `config.example.yaml` for the full provider schema. Minimal example:

```yaml
notes_dir: ~/Notes
capture_dir: ~/Notes/_capture-staging   # legacy: iOS-Shortcuts staging folder

providers:
  transcription:
    default: whisper_local
  title:
    default: ollama_local
  correction:
    default: claude
    claude:
      model: claude-sonnet-4-20250514
      api_key: env:ANTHROPIC_API_KEY

defaults:
  tags:
    - kernel
    - captured

metis:
  serendipity_age_days: 30
  max_connections: 3
  max_keywords: 10
```

## Features

### Note format

Notes land at the root of the notes directory as `YYYYMMDDHHMM - Title.md`, with
frontmatter that is valid YAML:

```yaml
---
title: Cypherpunk Mailing List as Unauthorized Workshop
author: Charles Berret
date: 2026-09-04 14:51
tags: [kernel, captured, llm/qwen-capable, cypherpunks, tools]
---
```

Tags are a YAML flow sequence — **not** `[[wikilinks]]`. Capture deliberately
does not stamp the `kind` / `subject` / `status` / `source` contract; a separate
classification pass owns those fields.

### Smart titles
Uses Ollama to generate concise 3-8 word titles. Falls back to first-line truncation for short content or when Ollama is unavailable.

### Fragments

A captured thought often lands as a few words — enough to remember, not enough
to work from. `capture fragments` scans the notes root for bodies under 200
characters and files an expansion item per fragment on the tree's Kettle desk
(`.kettle/runtime/queue.json`), so a sweep can prompt you to grow them.

```bash
capture fragments               # report only (default)
capture fragments --write       # file the entries
capture fragments --threshold 280 --write
```

Notes are never modified — the frontmatter contract belongs to `notes-process`,
and being a fragment is a fact *about* a note, not a property of it. That means
a dismissal lives on the desk: mark an entry `dismissed` and it is never re-filed,
however many times you rescan. This matters because length alone cannot tell a
seed from a complete-but-terse claim, so some entries are meant to be dismissed.

An empty note gets a different ask — write it or delete it — and is explicitly
flagged as something not to hand a model, since with nothing to read it will
invent something plausible.

### Metis cultivation
- **Auto-tags**: LLM-suggested tags added alongside base tags
- **Connection finder**: Surfaces related notes based on keyword overlap
- **Serendipity**: Shows a random old note for unexpected inspiration

Disable with `export CAPTURE_METIS=false` or set `llm.enable_metis: false` in config.

### Whisper dictionary
Custom vocabulary and post-processing corrections for voice transcription. Create
a YAML file:

```yaml
prompt_vocab:
  - Diffie-Hellman
  - cypherpunk
  - Zimmermann
corrections:
  "Zimmerman": "Zimmermann"
  "cypher punk": "cypherpunk"
```

Point to it with `whisper_dictionary` in config, or place `whisper-dictionary.yaml` next to your notes directory.

### Ollama model

The default model name is `qwen-capable`; any Ollama model works — override
with `providers.title.ollama_local.model`, or `OLLAMA_MODEL` in the
environment to override every stage at once. On an M3 Pro a title takes
~4-5s once the model is resident, so the stage timeouts (60s title / 45s
tags) are sized for a cold load rather than a warm one. The tool warms up
Ollama in the background while you type, so the model is ready when needed.

### GPU-host fence

On the GPU host the raw Ollama daemon listens on `127.0.0.1:11435`, and the
shell's `OLLAMA_HOST` points there. Capture does not follow that variable.
Title, tag, and correction calls `POST /api/generate` to the configured
`host`, which defaults to `http://127.0.0.1:11434` — the tinpusher fence. That
proxy runs the same admission decision as `gpu-admit`. A local tag is admitted
at the fence; capture never knocks `:11435` itself. Point
`providers.*.ollama_local.host` somewhere else only when you mean a different
daemon (a Mac's own Ollama on the same port is the usual case). The test suite
stubs these stages and does not need a live daemon.

## iOS app (the phone path)

A native SwiftUI app lives in `ios/`. It writes the same `.md` notes directly
to your Notes folder (e.g. iCloud Drive/Notes) — no staging step.

The photo loop is **highlight-confirm-memo** — the agent never writes behind
your back:

1. **Photograph** a print or handwritten page (camera or VisionKit scanner).
2. **See the OCR** — Apple Vision text is shown to you, not silently stored.
3. **Highlight** the span that becomes the note body. Saving without a
   selection is refused.
4. The **agent proposes title + tags**; you confirm (edit allowed) and may add
   a short memo, which appends to the body.
5. **Then** the note is written, in the same `YYYYMMDDHHMM - Title.md` shape
   the CLI writes.

```bash
cd ios && xcodegen generate && open Capture.xcodeproj
```

See [ios/README.md](ios/README.md) for setup (folder picker, Gemini API key in Keychain).

| Mode | iOS | Mac CLI |
|------|-----|---------|
| Transcription | Gemini Flash | Whisper |
| Title / tags | Gemini Flash | Ollama |
| OCR | Apple Vision | Apple Vision |
| Correction | disabled | Ollama / Claude |
| Auto-save | never — human confirms | n/a (you invoked it) |

## iOS Shortcuts (legacy)

**Legacy path, superseded by the native app above.** Still works; kept for
existing installs. Nothing new should be built on it.

Create iOS Shortcuts that save to the staging folder, then process with
`capture process`:

### Capture Text
1. **Ask for Input** (Question: "What's your idea?", Type: Text)
2. **Save File** to `iCloud Drive/Notes/_capture-staging/Text-[Current Date].txt`

### Capture Voice
1. **Record Audio** (Start: Immediately, Finish: On Tap)
2. **Save File** to `iCloud Drive/Notes/_capture-staging/Voice-[Current Date].m4a`

### Capture Scan
1. **Scan Document** (uses VisionKit scanner with edge detection)
2. **Save File** to `iCloud Drive/Notes/_capture-staging/Scan-[Current Date].pdf`

### Processing (legacy)

```bash
capture process
```

Transcribes audio with Whisper, OCRs images and PDFs with Apple Vision, creates notes with smart titles, and sends a macOS notification when complete.

## Project layout

```
capture/
├── cli.py                 # CLI entry point
├── core/
│   ├── config.py          # Config + provider defaults
│   ├── pipeline.py        # Extract → refine → enrich orchestration
│   ├── note.py            # Note formatting and Metis display
│   ├── vocabulary.py      # Whisper dictionary helpers
│   └── prompts/           # Shared prompt templates
├── providers/
│   ├── registry.py        # Per-stage provider resolution
│   ├── transcription/     # whisper_local, gemini_flash
│   ├── ocr/               # apple_vision, tesseract
│   ├── enrich/            # ollama_local, gemini_flash, truncate
│   ├── refine/            # ollama_local, gemini_flash, claude
│   └── connections/       # keyword search
└── platforms/
    ├── mac.defaults.yaml
    └── ios.defaults.yaml
ios/                       # Native SwiftUI app (the phone path)
tests/                     # pytest; offline by construction
```

## How it works

```
Mac CLI:  capture quick/text/voice/photo  ──▶  ~/Notes/  (timestamped .md)

iOS (native app — the phone path):
┌──────────────┐   camera → OCR shown → highlight →   ┌─────────────┐
│ iPhone       │   agent title+tags → confirm + memo  │ Notes folder │
│ Capture app  │ ────────────── human gate ─────────▶ │ same .md    │
└──────────────┘                                       └─────────────┘

iOS (legacy — Shortcuts):  iPhone Shortcuts → _capture-staging/ → `capture process`
```

Extraction: Apple Vision OCR (images, PDFs) · Whisper (voice) · Gemini Flash (iOS voice).
Enrichment: Ollama (Mac titles/tags) · Gemini Flash (iOS titles/tags) · always overridable per stage.

## Tests

```bash
.venv/bin/pytest tests/ -q
```

`tests/test_note_contract.py` pins the frontmatter contract — tags as a YAML
flow sequence, scalars quoted when they would otherwise misparse.
`tests/test_capture_floor.py` pins the whole capture path with every provider
disabled — the suite needs no model and no network. Run it before touching
anything that writes a note.

## License

MIT
