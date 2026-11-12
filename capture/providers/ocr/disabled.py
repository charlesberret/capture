"""Disabled OCR provider."""

from __future__ import annotations

from pathlib import Path


class DisabledOCRProvider:
    def extract(self, filepath: Path) -> str | None:
        return None
