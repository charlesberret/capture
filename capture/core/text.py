"""Text sanitising shared by the note writer and the local-model providers."""

from __future__ import annotations

import re

# `ollama run` emits spinner and cursor escapes even when stdout is captured
# rather than attached to a TTY. Written into frontmatter these make the whole
# YAML block unparseable — which is how one note was corrupted on 2026-09-05.
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[()][A-B0-2]|\x1b[=><]")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences, payload included."""
    if not text:
        return ""
    return ANSI_RE.sub("", text)


def strip_control(text: str, *, keep_newlines: bool = True) -> str:
    """Drop control characters that survive escape-sequence removal."""
    if not text:
        return ""
    return "".join(
        ch for ch in text if (ch == "\n" and keep_newlines) or ord(ch) >= 32
    )


def clean_model_output(text: str) -> str:
    """Sanitise raw local-model stdout for use in a note."""
    return strip_control(strip_ansi(text)).strip()
