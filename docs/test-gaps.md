# Capture test-gap analysis

Sprint work item: enumerate module coverage, name the riskiest untested behaviours, and add offline tests for the worst gaps. No production behaviour changes.

## How coverage was measured

Command (from the repository root, with PyYAML and pytest-cov installed in a local venv):

```bash
.venv/bin/pip install -e ".[yaml]" pytest pytest-cov pyyaml
.venv/bin/python -m pytest tests/ -q --cov=capture --cov-report=term-missing
```

Summary lines (after adding `tests/test_gaps.py`):

```
TOTAL                                          1526    832    45%
87 passed, 5 skipped in 0.43s
```

Five tests are skipped when optional platform tooling is absent (see `tests/test_process.py`).

## Coverage by module

| Module | Stmts | Miss | Cover |
|--------|------:|-----:|------:|
| `capture/__init__.py` | 1 | 0 | 100% |
| `capture/__main__.py` | 3 | 3 | 0% |
| `capture/cli.py` | 128 | 128 | 0% |
| `capture/core/__init__.py` | 0 | 0 | 100% |
| `capture/core/config.py` | 116 | 10 | 91% |
| `capture/core/fragments.py` | 99 | 13 | 87% |
| `capture/core/note.py` | 138 | 26 | 81% |
| `capture/core/pipeline.py` | 265 | 162 | 39% |
| `capture/core/prompts_loader.py` | 10 | 0 | 100% |
| `capture/core/state.py` | 3 | 0 | 100% |
| `capture/core/text.py` | 13 | 2 | 85% |
| `capture/core/ui.py` | 136 | 136 | 0% |
| `capture/core/vocabulary.py` | 87 | 13 | 85% |
| `capture/providers/__init__.py` | 0 | 0 | 100% |
| `capture/providers/_http.py` | 34 | 25 | 26% |
| `capture/providers/base.py` | 4 | 4 | 0% |
| `capture/providers/connections/disabled.py` | 4 | 1 | 75% |
| `capture/providers/connections/keyword.py` | 33 | 7 | 79% |
| `capture/providers/enrich/disabled.py` | 3 | 1 | 67% |
| `capture/providers/enrich/gemini.py` | 38 | 38 | 0% |
| `capture/providers/enrich/ollama.py` | 36 | 7 | 81% |
| `capture/providers/enrich/truncate.py` | 6 | 0 | 100% |
| `capture/providers/ocr/apple_vision.py` | 90 | 81 | 10% |
| `capture/providers/ocr/disabled.py` | 4 | 0 | 100% |
| `capture/providers/ocr/tesseract.py` | 14 | 8 | 43% |
| `capture/providers/ollama_http.py` | 29 | 8 | 72% |
| `capture/providers/refine/claude.py` | 21 | 21 | 0% |
| `capture/providers/refine/disabled.py` | 3 | 1 | 67% |
| `capture/providers/refine/gemini.py` | 21 | 21 | 0% |
| `capture/providers/refine/ollama.py` | 14 | 2 | 86% |
| `capture/providers/registry.py` | 85 | 30 | 65% |
| `capture/providers/transcription/disabled.py` | 4 | 0 | 100% |
| `capture/providers/transcription/gemini.py` | 30 | 30 | 0% |
| `capture/providers/transcription/whisper.py` | 54 | 54 | 0% |

Package total: **45%** line coverage (832 / 1526 statements missed).

### What is already well pinned

- **Note contract** (`tests/test_note_contract.py`, `tests/test_capture_floor.py`, `tests/test_reprocess_contract.py`): filename shape, YAML frontmatter, tag flow sequences, offline full-path `capture_quick`.
- **Config precedence** (`tests/test_config.py`): env overrides, legacy `llm:` merge, metis toggles.
- **Fragments desk** (`tests/test_fragments.py`): scan thresholds, queue shape, no note mutation.
- **Provider registry errors** (`tests/test_registry.py`): unknown stage/backend failures with a disabled config.

### Largest holes

- **CLI and UI** (`cli.py`, `ui.py`): zero coverage; everything is argparse and terminal interaction.
- **Pipeline orchestration** (`pipeline.py`, 39%): voice record, photo ingest, editor launch, async transcription, and correction routing.
- **Live-model backends** (`whisper`, `gemini`, `claude`, cloud OCR): intentionally untested offline; only `disabled` / `truncate` / mocked HTTP paths run in CI.
- **HTTP helper** (`_http.py`, 26%): real sockets only when a provider runs.

## Ten riskiest untested behaviours

Ranked by user-visible impact and lack of automated proof:

1. **CLI subcommand wiring** — wrong argparse setup could ship a command that exits successfully without writing a note, or points at the wrong pipeline entry (entire `cli.py` untested).
2. **Interactive terminal UI** — picker loops, recent-note display, and error surfacing in `ui.py` have no regression harness.
3. **Voice capture end-to-end** — `record_audio` → `transcribe_audio` → optional correction → `create_note` (including ffmpeg device discovery) is largely unexercised offline.
4. **Photo / PDF ingest** — `capture_photo` and Apple Vision / Tesseract fallbacks; OCR fallback chain in `ocr_image` when the primary provider returns empty text.
5. **Whisper local transcription** — model load, audio decode, and vocabulary-conditioned prompts (`whisper.py` at 0%); only the disabled stub is proven.
6. **Remote enrichment failures** — Gemini/Claude/Ollama HTTP timeouts, malformed JSON, and empty responses in title/tags/correction stages (most cloud modules at 0%).
7. **Metis serendipity during `create_note`** — random old-note surfacing depends on filesystem mtimes and YAML parsing inside `surface_serendipity`; was untested until the new gap test.
8. **`llm/*` model tags in frontmatter** — `_model_tag_for_note` derives tags from provider defaults; mis-derivation pollutes downstream indexers.
9. **Keyword connection false positives/negatives** — `KeywordConnectionsProvider` threshold (`matches >= 2`) and exclusion of the note just written (partially covered in contract tests, not the happy-path link).
10. **Fragments queue idempotency** — refiling the same fragment, settled statuses, and malformed desk JSON (`fragments.py` lines 138–149 still uncovered).

## New gap-filling tests

Added in `tests/test_gaps.py` (15 tests, all offline):

| Test | Gap addressed |
|------|----------------|
| `test_slugify_keeps_only_first_line_and_strips_illegal_filename_chars` | Filename slug rules beyond the floor tests |
| `test_create_note_raises_when_notes_dir_unset` | Guard rail when `NOTES_DIR` is unset |
| `test_model_tag_for_note_from_ollama_title_default` | `llm/*` tag derivation from Ollama config |
| `test_surface_serendipity_surfaces_an_old_note` | Metis serendipity selection and preview |
| `test_load_whisper_dictionary_reads_notes_dir_file` | Vocabulary YAML load path |
| `test_build_whisper_prompt_includes_vocabulary_terms` | Whisper prompt assembly |
| `test_apply_corrections_is_case_insensitive` | Post-transcription correction map |
| `test_flatten_vocabulary_dedupes_across_topics` | Vocab flattening for correction hints |
| `test_transcribe_audio_returns_none_when_transcription_disabled` | Pipeline noop when transcription disabled |
| `test_ocr_image_returns_none_when_ocr_disabled` | Pipeline noop when OCR disabled |
| `test_load_prompt_reads_bundled_title_template` | Prompt template bundle integrity |
| `test_format_prompt_substitutes_kwargs` | Prompt `.format` wiring used by Ollama providers |
| `test_resolve_secret_reads_environment` | `env:VAR` secret resolution |
| `test_keyword_connections_finds_notes_with_overlapping_keywords` | Keyword Metis connection happy path |
| `test_ollama_title_strips_title_prefix_from_model_output` | Ollama title parsing (HTTP mocked) |

These raised package coverage from **39%** to **45%** and `capture/core/note.py` from **59%** to **81%** on the same command as above.

## Suggested next steps (out of scope here)

- Characterise `cli.py` with `pytest` using `capsys` and argv injection for each subcommand's `--help` and dry-run paths.
- Extract pure functions from `pipeline.py` (device parsing, staging paths) for unit tests without ffmpeg.
- Keep cloud/Whisper backends behind mocks mirroring `test_ollama_title_strips_title_prefix_from_model_output`.
