# Capture agent guide

Capture is a Python package and CLI that turns text, audio, and images into timestamped Markdown notes.

- Work only in this repository.
- Run tests with `.venv/bin/python -m pytest -q`.
- Stub model providers or select their `disabled` backends in tests and CI. Never require live Ollama, Gemini, Whisper, OCR, or network services.
- Notes use the filename `{YYYYMMDDHHMM} - {slug}.md`. Each note contains YAML frontmatter with `title`, `date`, and `tags`, followed by the captured text as its body.
