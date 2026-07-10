"""Disabled connections provider."""

from pathlib import Path


class DisabledConnectionsProvider:
    def find(self, content: str, *, notes_dir: Path) -> list[str]:
        return []
