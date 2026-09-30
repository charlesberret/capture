"""Ollama correction/refine provider.

Same fence as titles and tags: HTTP to the configured host, never `ollama run`.
"""

from __future__ import annotations

from capture.core.prompts_loader import format_prompt
from capture.providers.ollama_http import ollama_complete


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
        corrected = ollama_complete(self.cfg, prompt)
        if corrected and 0.5 < len(corrected) / max(len(text), 1) < 2.0:
            return corrected
        return text
