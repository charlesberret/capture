---
project: capture
kind: software
phase: active
canonical: ~/cloud/git-projects/capture
deps: pip
test_cmd: none
test_signal: none
healthbeacon: none
---

## Status

Quick multi-modal note capture CLI — text, voice, images, PDFs, and an iOS staging folder — producing timestamped markdown notes with LLM-generated titles and tags (Ollama-backed, optional). Refactored 2026-07-09 from a single script into a package with per-feature model providers; a topic-keyed whisper dictionary and upgraded default model landed 2026-07-06. The working tree carries an uncommitted `ios/` component plus README and .gitignore edits from that refactor.

## Next action

- [ ] Commit or discard the uncommitted `ios/` directory and the README/.gitignore edits left over from the provider refactor

## Known gaps

- No test suite — nothing verifies the CLI or the provider plumbing
- Deps declared in `pyproject.toml` only; no `requirements.txt`/lock, so dep-freshness reads blind
- No healthbeacon
