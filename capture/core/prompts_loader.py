"""Load prompt templates from core/prompts/."""

from pathlib import Path

from capture.core.config import PROMPTS_DIR

_cache: dict[str, str] = {}


def load_prompt(name: str) -> str:
    if name not in _cache:
        path = PROMPTS_DIR / f"{name}.txt"
        _cache[name] = path.read_text()
    return _cache[name]


def format_prompt(name: str, **kwargs: str) -> str:
    return load_prompt(name).format(**kwargs)
