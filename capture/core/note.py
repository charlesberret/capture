"""Note formatting and filesystem helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from capture.core import state
from capture.core.config import cfg, metis_enabled
from capture.core.text import strip_ansi, strip_control
from capture.providers.registry import get_provider


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M")


def slugify(text: str, max_len: int = 50) -> str:
    first_line = text.split("\n")[0].strip()
    slug = first_line[:max_len].strip()
    for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
        slug = slug.replace(char, "")
    return slug.strip(" .")


def normalize_tag(tag: str) -> str | None:
    """Reduce a tag to the bare form used in the notes frontmatter contract.

    Accepts legacy ``[[wikilink]]`` and ``llm:model`` spellings (both of which
    the 2026 bracket-fix pass migrated away from) and returns ``kernel`` /
    ``llm/qwen``. Characters that would break a YAML flow sequence are dropped.
    """
    if not tag:
        return None
    tag = tag.strip()
    while tag.startswith("[[") and tag.endswith("]]"):
        tag = tag[2:-2].strip()
    tag = tag.replace(":", "/")
    # Escape sequences first, then any control bytes left over: dropping the
    # ESC alone would leave its "[2D" payload behind as literal text.
    tag = strip_control(strip_ansi(tag), keep_newlines=False)
    for char in ("[", "]", ",", "{", "}", "#", "&", "*", '"', "'"):
        tag = tag.replace(char, "")
    tag = " ".join(tag.split())
    return tag or None


def yaml_scalar(value: str) -> str:
    """Quote a frontmatter scalar when bare YAML would misparse it."""
    text = str(value).strip()
    if not text:
        return '""'
    needs_quote = (
        text[0] in "[]{}>|*&!%@`#-?:,'\""
        or ": " in text
        or text.endswith(":")
        or text.lower() in ("true", "false", "null", "yes", "no", "on", "off", "~")
    )
    if needs_quote:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def format_tags(tags: list[str]) -> str:
    """Serialise tags as a YAML flow sequence: ``[kernel, captured]``."""
    seen: list[str] = []
    for raw in tags:
        tag = normalize_tag(raw)
        if tag and tag not in seen:
            seen.append(tag)
    return "[" + ", ".join(seen) + "]"


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


def find_connections(content: str, exclude: Path | None = None) -> list[str]:
    if not metis_enabled():
        return []
    provider = get_provider("connections")
    notes_dir = state.NOTES_DIR
    if notes_dir is None:
        return []
    return provider.find(content, notes_dir=notes_dir, exclude=exclude)


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
            # Skip the frontmatter block outright — previewing "kind: atom"
            # tells you nothing about the note.
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    text = parts[2]
            lines = [l for l in text.split("\n") if l.strip()]
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

    tags_str = format_tags(base_tags)
    author = cfg()["defaults"]["author"]
    author_line = f"\nauthor: {yaml_scalar(author)}" if author else ""
    title_value = yaml_scalar(slug if slug else "Untitled capture")
    note_content = f"""---
title: {title_value}{author_line}
date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
tags: {tags_str}
---

{content}
"""

    filepath.write_text(note_content)
    print(f"✓ Created: {filepath.name}")

    if metis_enabled():
        connections = find_connections(content, exclude=filepath)
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
                return f"llm/{model.split(':')[0]}"
        elif name == "gemini_flash":
            model = config["providers"][stage]["gemini_flash"].get("model", "gemini")
            return f"llm/{model.split('-')[0]}"
    return None
