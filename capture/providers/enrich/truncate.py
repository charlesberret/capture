"""Truncate title provider — no LLM."""

from __future__ import annotations

from capture.core.note import slugify


class TruncateTitleProvider:
    def generate(self, content: str, warmup=None) -> str | None:
        slug = slugify(content)
        return slug or None
