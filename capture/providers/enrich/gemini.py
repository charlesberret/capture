"""Gemini Flash providers for title and tag enrichment."""

from __future__ import annotations

from capture.core.config import resolve_secret
from capture.core.prompts_loader import format_prompt
from capture.providers._http import gemini_generate


class GeminiTitleProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def generate(self, content: str, warmup=None) -> str | None:
        api_key = resolve_secret(self.cfg.get("api_key"))
        if not api_key:
            return None
        prompt = format_prompt("title", content=content[:1000])
        try:
            raw = gemini_generate(
                api_key=api_key,
                model=self.cfg.get("model", "gemini-2.0-flash"),
                contents=[{"parts": [{"text": prompt}]}],
                timeout=self.cfg.get("timeout", 20),
            )
        except Exception:
            return None
        if not raw:
            return None
        title = raw.strip("\"'")
        if title.lower().startswith("title:"):
            title = title[6:].strip()
        return title if title and len(title) < 80 else None


class GeminiTagsProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def suggest(self, content: str, warmup=None) -> list[str]:
        api_key = resolve_secret(self.cfg.get("api_key"))
        if not api_key:
            return []
        prompt = format_prompt("tags", content=content[:500])
        try:
            raw = gemini_generate(
                api_key=api_key,
                model=self.cfg.get("model", "gemini-2.0-flash"),
                contents=[{"parts": [{"text": prompt}]}],
                timeout=self.cfg.get("timeout", 15),
            )
        except Exception:
            return []
        if not raw:
            return []
        tags = [t.strip().strip("\"'") for t in raw.split(",")]
        return [f"[[{tag}]]" for tag in tags if tag and len(tag) < 30]
