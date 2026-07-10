"""Disabled OCR provider."""

from pathlib import Path


class DisabledOCRProvider:
    def extract(self, filepath: Path) -> str | None:
        return None
