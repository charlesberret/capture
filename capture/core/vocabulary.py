"""Whisper dictionary loading and vocabulary helpers."""

from __future__ import annotations

from pathlib import Path

from capture.core import state
from capture.core.config import cfg

_DEFAULT_TEMPLATES = {
    "general": "This is a voice memo that may reference {terms}.",
    "crypto": "This discussion covers cryptography and cybersecurity history, including {terms}.",
    "philosophy": "This lecture discusses philosophical concepts including {terms}.",
    "journalism": "This is about journalism, media, and investigative reporting, referencing {terms}.",
    "academic": "This is an academic discussion referencing {terms}.",
}


def load_whisper_dictionary(
    notes_dir: Path | None = None,
) -> tuple[dict[str, list[str]], dict[str, str], dict[str, str]]:
    """Load vocab, corrections, and prompt templates from whisper-dictionary.yaml."""
    try:
        import yaml
    except ImportError:
        return {}, {}, dict(_DEFAULT_TEMPLATES)

    notes_dir = notes_dir or state.NOTES_DIR
    vocab_by_topic: dict[str, list[str]] = {}
    corrections: dict[str, str] = {}
    templates = dict(_DEFAULT_TEMPLATES)

    dict_paths: list[Path] = []
    sys_dict = cfg().get("whisper_dictionary")
    if sys_dict:
        dict_paths.append(Path(sys_dict).expanduser())
    if notes_dir:
        dict_paths.extend(
            [notes_dir / "whisper-dictionary.yaml", notes_dir.parent / "whisper-dictionary.yaml"]
        )

    for dict_path in dict_paths:
        if not dict_path.exists():
            continue
        try:
            data = yaml.safe_load(dict_path.read_text()) or {}
            pv = data.get("prompt_vocab")
            if pv:
                if isinstance(pv, list):
                    vocab_by_topic.setdefault("general", []).extend(pv)
                elif isinstance(pv, dict):
                    for topic, terms in pv.items():
                        if isinstance(terms, list):
                            vocab_by_topic.setdefault(topic, []).extend(terms)
            if data.get("corrections"):
                corrections.update(data["corrections"])
            if data.get("prompt_templates"):
                templates.update(data["prompt_templates"])
        except Exception:
            pass

    return vocab_by_topic, corrections, templates


def flatten_vocabulary(vocab_by_topic: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for topic_terms in vocab_by_topic.values():
        for term in topic_terms:
            if term not in seen:
                seen.add(term)
                terms.append(term)
    return terms


def _count_whisper_tokens(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("gpt2")
        return len(enc.encode(text))
    except ImportError:
        return int(len(text.split()) * 1.3)


def build_whisper_prompt(
    vocab_by_topic: dict[str, list[str]],
    templates: dict[str, str],
    topic: str = "general",
) -> str | None:
    terms: list[str] = []
    if topic != "general" and topic in vocab_by_topic:
        terms.extend(vocab_by_topic[topic])
    terms.extend(vocab_by_topic.get("general", []))
    for t, t_terms in vocab_by_topic.items():
        if t not in (topic, "general"):
            terms.extend(t_terms)

    seen: set[str] = set()
    unique_terms: list[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique_terms.append(t)
    terms = unique_terms

    if not terms:
        return None

    template = templates.get(topic, templates.get("general", "This is a voice memo referencing {terms}."))
    while terms:
        prompt = template.format(terms=", ".join(terms))
        if _count_whisper_tokens(prompt) <= 224:
            return prompt
        terms.pop(0)
    return None


def apply_corrections(text: str, corrections: dict[str, str]) -> str:
    if not corrections:
        return text
    import re

    for wrong, right in corrections.items():
        text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
    return text
