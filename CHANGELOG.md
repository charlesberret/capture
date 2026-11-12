# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 1.1.0

### Added

- `capture fragments` scans the notes directory for bodies shorter than a threshold and files expansion items on the Kettle desk (report-only by default; `--write` updates the queue).
- Offline pytest suite with all model providers disabled; CI runs it on push and pull request.
- Native iOS app in `ios/` for photograph → OCR → highlight → confirm → note (same markdown contract as the CLI).

### Changed

- README rewritten for a public audience; house-specific host and proxy details removed from docs and example config.
- Provider registry and config precedence pinned in tests; OCR honors a disabled stage for images and PDFs.

### Fixed

- `capture process` keeps staging files when no note is written.
- Staging folder naming in the process CLI.
