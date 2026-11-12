"""Record title-provider failures for stderr and optional note frontmatter."""

from __future__ import annotations

import sys

_reported_this_capture: set[str] = set()
_pending_frontmatter: str | None = None


def begin_title_capture() -> None:
    """Reset per-note dedup before attempting title generation."""
    _reported_this_capture.clear()
    global _pending_frontmatter
    _pending_frontmatter = None


def report_title_provider_failure(provider: str, reason: str) -> None:
    """Emit one stderr line per failure per capture; stash for frontmatter."""
    global _pending_frontmatter
    reason = " ".join(str(reason).split())
    if not reason:
        reason = "unknown error"
    line = f"{provider}: {reason}"
    _pending_frontmatter = line
    if line in _reported_this_capture:
        return
    _reported_this_capture.add(line)
    print(f"capture: title provider {line}", file=sys.stderr)


def consume_title_provider_failure() -> str | None:
    """Return the failure line for this capture, if any."""
    global _pending_frontmatter
    value = _pending_frontmatter
    _pending_frontmatter = None
    return value
