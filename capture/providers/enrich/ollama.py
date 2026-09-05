"""Ollama providers for title and tag enrichment."""

from __future__ import annotations

import subprocess

from capture.core.prompts_loader import format_prompt
from capture.core.text import clean_model_output


def _ollama_run(model: str, prompt: str, timeout: int) -> str | None:
    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return clean_model_output(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _wait_warmup(warmup_proc, timeout: int = 90) -> None:
    """Wait for a background warmup to finish loading the model.

    Never kill it on timeout: the warmup exists to get a multi-GB model
    resident in the Ollama server, and killing it mid-load forfeits exactly
    the work we were waiting on, so the real call pays the cold start again.
    """
    if not warmup_proc:
        return
    try:
        warmup_proc.wait(timeout=timeout)
    except Exception:
        pass


class OllamaTitleProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def warmup(self):
        try:
            return subprocess.Popen(
                ["ollama", "run", self.cfg.get("model", "qwen-capable"), "hi"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            return None

    def generate(self, content: str, warmup=None) -> str | None:
        _wait_warmup(warmup)
        prompt = format_prompt("title", content=content[:1000])
        raw = _ollama_run(
            self.cfg.get("model", "qwen-capable"),
            prompt,
            self.cfg.get("timeout", 20),
        )
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
        raw = _ollama_run(
            self.cfg.get("model", "qwen-capable"),
            prompt,
            self.cfg.get("timeout", 15),
        )
        if not raw:
            return []
        tags = [t.strip().strip("\"'") for t in raw.split(",")]
        return [tag for tag in tags if tag and len(tag) < 30]
