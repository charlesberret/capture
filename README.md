# capture

Quick multi-modal note capture with LLM-powered titles and tags.

Captures ideas as timestamped markdown notes from text, voice, images, PDFs, or an iOS staging folder. Uses [Ollama](https://ollama.com) for smart title generation, auto-tagging, and serendipitous note connections.

## Install

```bash
# Option 1: symlink (simplest)
ln -s /path/to/capture/capture ~/.local/bin/capture

# Option 2: pipx
pipx install .

# Option 3: pip editable
pip install -e .
```

### Dependencies

**Required:** Python 3.9+

**Optional:**
- [Ollama](https://ollama.com) + a model (e.g. `ollama pull phi3:mini`) -- smart titles and tags
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
capture process            # Process staging folder (from iOS Shortcuts)
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

### Config precedence

1. Environment variables (`OLLAMA_MODEL`, `EDITOR`, `CAPTURE_METIS`)
2. Config file (`$CAPTURE_CONFIG` env var, or `~/.config/capture/config.yaml`)
3. Built-in defaults

### Config schema

```yaml
notes_dir: ~/Notes                    # Where notes are saved
capture_dir: ~/Notes/_capture-staging # Staging folder for iOS captures
whisper_dictionary: null              # Custom Whisper vocabulary/corrections
editor: nano                          # Editor for text captures

llm:
  model: phi3:mini          # Ollama model
  enable_metis: true        # Smart tags, connections, serendipity
  title_timeout: 20         # Seconds for title generation
  tag_timeout: 15           # Seconds for tag suggestion
  content_threshold: 30     # Min chars before LLM title attempt
  whisper_model: base       # Whisper model size

defaults:
  tags:                     # Base tags on every capture
    - "[[kernel]]"
    - "[[captured]]"
  author: ""                # Omitted from frontmatter when empty

metis:
  serendipity_age_days: 30  # Age threshold for serendipity surfacing
  max_connections: 3        # Related notes to show
  max_keywords: 10          # Keywords for connection search

ui:
  max_recent: 5             # Recent destinations to remember
```

## Features

### Smart titles
Uses Ollama to generate concise 3-8 word titles. Falls back to first-line truncation for short content or when Ollama is unavailable.

### Metis cultivation
- **Auto-tags**: LLM-suggested tags added alongside base tags
- **Connection finder**: Surfaces related notes based on keyword overlap
- **Serendipity**: Shows a random old note for unexpected inspiration

Disable with `export CAPTURE_METIS=false` or set `llm.enable_metis: false` in config.

### Whisper dictionary
Custom vocabulary and post-processing corrections for voice transcription. Create a YAML file:

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

### Ollama model benchmarks

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| **phi3:mini** | 1.9GB | 2-4s | Excellent titles, rich tags |
| gemma2:2b | 1.6GB | 1.6-2s | Concise titles, fewer tags |
| llama3.2:1b | 1.3GB | 40s | Frequent timeouts |
| llama3.1:latest | 4.9GB | 20s+ | Too slow |

The tool warms up Ollama in the background while you type, so the model is ready when needed.

## iOS Shortcuts

Create iOS Shortcuts that save to the staging folder, then process with `capture process`.

### Capture Text
1. **Ask for Input** (Question: "What's your idea?", Type: Text)
2. **Save File** to `iCloud Drive/Notes/_capture-staging/Text-[Current Date].txt`

### Capture Voice
1. **Record Audio** (Start: Immediately, Finish: On Tap)
2. **Save File** to `iCloud Drive/Notes/_capture-staging/Voice-[Current Date].m4a`

### Capture Scan
1. **Scan Document** (uses VisionKit scanner with edge detection)
2. **Save File** to `iCloud Drive/Notes/_capture-staging/Scan-[Current Date].pdf`

### Processing

```bash
capture process
```

Transcribes audio with Whisper, OCRs images and PDFs with Apple Vision, creates notes with smart titles, and sends a macOS notification when complete.

## How it works

```
CLI:  capture quick/text/voice/photo  ──▶  ~/Notes/ (timestamped .md)

iOS:
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│ iPhone      │     │ _capture-staging/ │     │ ~/Notes/     │
│ Shortcuts   │ ──▶ │ (iCloud sync)    │ ──▶ │ Kernel notes │
└─────────────┘     └──────────────────┘     └──────────────┘
                          │
              Apple Vision OCR (images, PDFs)
              Whisper (voice transcription)
              Ollama (title generation, tagging)
```

## License

MIT
