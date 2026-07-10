"""Tesseract OCR fallback provider."""

from __future__ import annotations

import subprocess
from pathlib import Path


class TesseractProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def extract(self, filepath: Path) -> str | None:
        try:
            lang = self.cfg.get("lang", "eng")
            result = subprocess.run(
                ["tesseract", str(filepath), "stdout", "-l", lang],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception as e:
            print(f"Tesseract OCR failed: {e}")
            return None
