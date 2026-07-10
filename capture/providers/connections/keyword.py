"""Keyword-based note connection finder."""

from __future__ import annotations

from pathlib import Path


class KeywordConnectionsProvider:
    def __init__(self, provider_cfg: dict, config: dict):
        self.cfg = provider_cfg
        self.config = config

    def find(self, content: str, *, notes_dir: Path) -> list[str]:
        words = content.lower().split()
        keywords = [w for w in words if len(w) > 5][: self.config["metis"]["max_keywords"]]
        if not keywords:
            return []

        connections: list[str] = []
        try:
            for note_file in notes_dir.glob("*.md"):
                if note_file.name.startswith("_"):
                    continue
                try:
                    note_content = note_file.read_text().lower()
                    matches = sum(1 for kw in keywords if kw in note_content)
                    if matches >= 2:
                        title = note_file.stem
                        if " - " in title:
                            title = title.split(" - ", 1)[1]
                        connections.append(title)
                        if len(connections) >= self.config["metis"]["max_connections"]:
                            break
                except OSError:
                    continue
        except OSError:
            pass
        return connections
