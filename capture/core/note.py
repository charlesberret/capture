"""Note formatting and filesystem helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from capture.core import state
from capture.core.config import cfg, metis_enabled
from capture.providers.registry import get_provider


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M")


def slugify(text: str, max_len: int = 50) -> str:
    first_line = text.split("\n")[0].strip()
    slug = first_line[:max_len].strip()
    for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
        slug = slug.replace(char, "")
    return slug.strip(" .")


def generate_title(content: str, warmup=None) -> str:
    """Generate title via configured provider, with truncate fallback."""
    from capture.core.config import content_threshold

    if len(content.strip()) > content_threshold():
        provider = get_provider("title")
        title = provider.generate(content, warmup=warmup)
        if title:
            return slugify(title, max_len=80)
    return slugify(content)


def suggest_tags(content: str, warmup=None) -> list[str]:
    if not metis_enabled():
        return []
    provider = get_provider("tags")
    return provider.suggest(content, warmup=warmup)


def find_connections(content: str) -> list[str]:
    if not metis_enabled():
        return []
    provider = get_provider("connections")
    notes_dir = state.NOTES_DIR
    if notes_dir is None:
        return []
    return provider.find(content, notes_dir=notes_dir)


def surface_serendipity() -> str | None:
    if not metis_enabled():
        return None

    import random

    notes_dir = state.NOTES_DIR
    if notes_dir is None:
        return None

    try:
        age_seconds = cfg()["metis"]["serendipity_age_days"] * 86400
        cutoff = datetime.now().timestamp() - age_seconds
        old_notes = [
            f
            for f in notes_dir.glob("*.md")
            if not f.name.startswith("_") and f.stat().st_mtime < cutoff
        ]
        if not old_notes:
            return None

        selected = random.choice(old_notes)
        title = selected.stem
        if " - " in title:
            title = title.split(" - ", 1)[1]

        try:
            text = selected.read_text()
            lines = [l for l in text.split("\n") if l.strip() and not l.startswith("---")]
            preview = lines[0][:100] if lines else ""
            return f"💡 Serendipity: {title}\n   {preview}..."
        except OSError:
            return f"💡 Serendipity: {title}"
    except OSError:
        return None


def create_note(content: str, title: str | None = None, warmup=None) -> Path:
    """Create a kernel note with frontmatter and optional Metis enrichment."""
    notes_dir = state.NOTES_DIR
    if notes_dir is None:
        raise RuntimeError("NOTES_DIR not set")

    ts = timestamp()
    if title:
        slug = slugify(title)
    else:
        slug = generate_title(content, warmup=warmup)

    filename = f"{ts} - {slug}.md" if slug else f"{ts}.md"
    filepath = notes_dir / filename

    base_tags = list(cfg()["defaults"]["tags"])
    if metis_enabled():
        model_tag = _model_tag_for_note()
        if model_tag:
            base_tags.append(model_tag)
        suggested = suggest_tags(content, warmup=warmup)
        if suggested:
            base_tags.extend(suggested)

    tags_str = ", ".join(base_tags)
    author = cfg()["defaults"]["author"]
    author_line = f"\nauthor: {author}" if author else ""
    note_content = f"""---
title: {slug if slug else 'Untitled capture'}{author_line}
date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
tags: {tags_str}
---

{content}
"""

    filepath.write_text(note_content)
    print(f"✓ Created: {filepath.name}")

    if metis_enabled():
        connections = find_connections(content)
        if connections:
            print(f"  🔗 Related: {', '.join(connections)}")
        serendipity = surface_serendipity()
        if serendipity:
            print(f"  {serendipity}")

    return filepath


def _model_tag_for_note() -> str | None:
    config = cfg()
    for stage in ("title", "tags"):
        name = config["providers"][stage]["default"]
        if name == "ollama_local":
            model = config["providers"][stage]["ollama_local"].get("model", "")
            if model:
                return f"[[llm:{model.split(':')[0]}]]"
        elif name == "gemini_flash":
            model = config["providers"][stage]["gemini_flash"].get("model", "gemini")
            return f"[[llm:{model.split('-')[0]}]]"
    return None
