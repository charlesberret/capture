"""Ollama correction/refine provider."""

from __future__ import annotations

import subprocess

from capture.core.prompts_loader import format_prompt
from capture.core.text import clean_model_output


class OllamaCorrectionProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def correct(self, text: str, *, source: str = "audio", vocabulary: str = "") -> str:
        if not vocabulary:
            return text
        prompt = format_prompt(
            "correction_audio",
            vocabulary=vocabulary,
            source=source,
            text=text,
        )
        try:
            result = subprocess.run(
                ["ollama", "run", self.cfg.get("model", "qwen-capable"), prompt],
                capture_output=True,
                text=True,
                timeout=self.cfg.get("timeout", 30),
            )
            if result.returncode == 0:
                corrected = clean_model_output(result.stdout)
                if corrected and 0.5 < len(corrected) / max(len(text), 1) < 2.0:
                    return corrected
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return text
