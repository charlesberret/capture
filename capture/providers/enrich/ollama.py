"""Ollama providers for title and tag enrichment.

Requests go to the configured HTTP host (the tinpusher fence on the GPU host),
not `ollama run`. See capture.providers.ollama_http.
"""

from __future__ import annotations

from capture.core.prompts_loader import format_prompt
from capture.providers.ollama_http import ollama_complete, ollama_warmup


def _wait_warmup(warmup, timeout: int = 90) -> None:
    if not warmup:
        return
    try:
        warmup.wait(timeout=timeout)
    except Exception:
        pass


class OllamaTitleProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def warmup(self):
        return ollama_warmup(self.cfg)

    def generate(self, content: str, warmup=None) -> str | None:
        _wait_warmup(warmup)
        prompt = format_prompt("title", content=content[:1000])
        raw = ollama_complete(self.cfg, prompt)
        if not raw:
            return None
        title = raw.strip("\"'")
        if title.lower().startswith("title:"):
            title = title[6:].strip()
        return title if title and len(title) < 80 else None


class OllamaTagsProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def suggest(self, content: str, warmup=None) -> list[str]:
        _wait_warmup(warmup)
        prompt = format_prompt("tags", content=content[:500])
        raw = ollama_complete(self.cfg, prompt)
        if not raw:
            return []
        tags = [t.strip().strip("\"'") for t in raw.split(",")]
        return [tag for tag in tags if tag and len(tag) < 30]
