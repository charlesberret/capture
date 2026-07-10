"""Gemini Flash correction/refine provider."""

from __future__ import annotations

from capture.core.config import resolve_secret
from capture.core.prompts_loader import format_prompt
from capture.providers._http import gemini_generate


class GeminiCorrectionProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def correct(self, text: str, *, source: str = "audio", vocabulary: str = "") -> str:
        if not vocabulary:
            return text
        api_key = resolve_secret(self.cfg.get("api_key"))
        if not api_key:
            return text
        prompt = format_prompt(
            "correction_audio",
            vocabulary=vocabulary,
            source=source,
            text=text,
        )
        try:
            corrected = gemini_generate(
                api_key=api_key,
                model=self.cfg.get("model", "gemini-2.0-flash"),
                contents=[{"parts": [{"text": prompt}]}],
                timeout=self.cfg.get("timeout", 30),
            )
            if corrected and 0.5 < len(corrected) / max(len(text), 1) < 2.0:
                return corrected
        except Exception:
            pass
        return text
