"""Configuration loading with per-feature provider registry."""

from __future__ import annotations

import copy
import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

DEFAULTS = {
    "notes_dir": "~/Notes",
    "capture_dir": "~/Notes/_capture-staging",
    "whisper_dictionary": None,
    "editor": "nano",
    "llm": {
        "model": "phi3:mini",
        "enable_metis": True,
        "title_timeout": 20,
        "tag_timeout": 15,
        "content_threshold": 30,
        "whisper_model": "medium",
        "whisper_backend": "python",
        "auto_correct": True,
        "correction_timeout": 30,
    },
    "defaults": {
        "tags": ["[[kernel]]", "[[captured]]"],
        "author": "",
    },
    "metis": {
        "serendipity_age_days": 30,
        "max_connections": 3,
        "max_keywords": 10,
    },
    "ui": {
        "max_recent": 5,
    },
}

MAC_PROVIDER_DEFAULTS = {
    "transcription": {
        "default": "whisper_local",
        "whisper_local": {
            "model": "medium",
            "backend": "python",
        },
        "gemini_flash": {
            "model": "gemini-2.0-flash",
            "api_key": "env:GOOGLE_API_KEY",
            "timeout": 120,
        },
        "disabled": {},
    },
    "ocr": {
        "default": "apple_vision",
        "apple_vision": {
            "recognition_level": "accurate",
            "language_correction": True,
        },
        "tesseract": {
            "lang": "eng",
        },
        "disabled": {},
    },
    "title": {
        "default": "ollama_local",
        "ollama_local": {
            "model": "phi3:mini",
            "host": "http://localhost:11434",
            "timeout": 20,
        },
        "gemini_flash": {
            "model": "gemini-2.0-flash",
            "api_key": "env:GOOGLE_API_KEY",
            "timeout": 20,
        },
        "truncate": {},
        "disabled": {},
    },
    "tags": {
        "default": "ollama_local",
        "ollama_local": {
            "model": "phi3:mini",
            "host": "http://localhost:11434",
            "timeout": 15,
        },
        "gemini_flash": {
            "model": "gemini-2.0-flash",
            "api_key": "env:GOOGLE_API_KEY",
            "timeout": 15,
        },
        "disabled": {},
    },
    "correction": {
        "default": "ollama_local",
        "ollama_local": {
            "model": "phi3:mini",
            "host": "http://localhost:11434",
            "timeout": 30,
        },
        "gemini_flash": {
            "model": "gemini-2.0-flash",
            "api_key": "env:GOOGLE_API_KEY",
            "timeout": 30,
        },
        "claude": {
            "model": "claude-sonnet-4-20250514",
            "api_key": "env:ANTHROPIC_API_KEY",
            "timeout": 60,
        },
        "disabled": {},
    },
    "connections": {
        "default": "keyword",
        "keyword": {},
        "disabled": {},
    },
}

DEFAULT_CONFIG_TEMPLATE = """\
# capture configuration
# Place at ~/.config/capture/config.yaml or set CAPTURE_CONFIG env var

# Where notes are saved (default: ~/Notes)
# notes_dir: ~/Notes

# Staging folder for iOS Shortcut captures (default: ~/Notes/_capture-staging)
# capture_dir: ~/Notes/_capture-staging

# Path to a whisper-dictionary.yaml for custom vocabulary / corrections
# whisper_dictionary: null

# Editor for text captures (default: nano)
# editor: nano

# Per-feature model providers (see config.example.yaml for full schema)
# providers:
#   transcription:
#     default: whisper_local
#   title:
#     default: ollama_local
#   tags:
#     default: ollama_local
#   correction:
#     default: ollama_local

# Legacy LLM settings (still honored; merged into providers when omitted)
# llm:
#   model: phi3:mini
#   enable_metis: true
#   title_timeout: 20
#   tag_timeout: 15
#   content_threshold: 30
#   whisper_model: medium
#   auto_correct: true

# Default note metadata
# defaults:
#   tags:
#     - "[[kernel]]"
#     - "[[captured]]"
#   author: ""

# Metis cultivation settings
# metis:
#   serendipity_age_days: 30
#   max_connections: 3
#   max_keywords: 10

# UI settings
# ui:
#   max_recent: 5
"""

_config: dict | None = None


def _deep_merge(base: dict, override: dict) -> dict:
    merged = base.copy()
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def _deep_copy_dict(d: dict) -> dict:
    return copy.deepcopy(d)


def _find_config_file() -> Path | None:
    env_path = os.environ.get("CAPTURE_CONFIG")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p
    default = Path.home() / ".config" / "capture" / "config.yaml"
    if default.exists():
        return default
    return None


def resolve_secret(value: str | None) -> str | None:
    """Resolve env:VAR references in config secret fields."""
    if not value or not isinstance(value, str):
        return value
    if value.startswith("env:"):
        return os.environ.get(value[4:]) or None
    return value


def _apply_legacy_llm(config: dict) -> dict:
    """Map legacy llm: settings into provider entries when not explicitly set."""
    llm = config.get("llm", {})
    providers = config.setdefault("providers", _deep_copy_dict(MAC_PROVIDER_DEFAULTS))

    model = llm.get("model", "phi3:mini")
    for stage in ("title", "tags", "correction"):
        stage_cfg = providers.setdefault(stage, {})
        ollama = stage_cfg.setdefault("ollama_local", {})
        if "model" not in ollama or ollama.get("model") == MAC_PROVIDER_DEFAULTS[stage]["ollama_local"]["model"]:
            ollama["model"] = model
        timeout_key = "timeout"
        llm_timeout = llm.get(f"{stage.replace('correction', 'correction')}_timeout")
        if stage == "title":
            llm_timeout = llm.get("title_timeout", 20)
        elif stage == "tags":
            llm_timeout = llm.get("tag_timeout", 15)
        elif stage == "correction":
            llm_timeout = llm.get("correction_timeout", 30)
        if llm_timeout is not None:
            ollama["timeout"] = llm_timeout

    whisper = providers.setdefault("transcription", {}).setdefault("whisper_local", {})
    if llm.get("whisper_model"):
        whisper["model"] = llm["whisper_model"]
    if llm.get("whisper_backend"):
        whisper["backend"] = llm["whisper_backend"]

    if not llm.get("enable_metis", True):
        providers["tags"]["default"] = "disabled"
        providers["connections"]["default"] = "disabled"

    if not llm.get("auto_correct", True):
        providers["correction"]["default"] = "disabled"

    return config


def load_config(config_path: str | Path | None = None) -> dict:
    """Load configuration: env vars > config file > platform defaults."""
    config = _deep_copy_dict(DEFAULTS)

    file_path = Path(config_path).expanduser() if config_path else _find_config_file()
    if file_path and file_path.exists():
        try:
            import yaml

            file_config = yaml.safe_load(file_path.read_text()) or {}
            config = _deep_merge(config, file_config)
        except ImportError:
            print(f"Warning: PyYAML not installed, cannot read {file_path}")
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")

    if "providers" not in config:
        config["providers"] = _deep_copy_dict(MAC_PROVIDER_DEFAULTS)
    else:
        config["providers"] = _deep_merge(
            _deep_copy_dict(MAC_PROVIDER_DEFAULTS), config["providers"]
        )

    config = _apply_legacy_llm(config)

    if os.environ.get("OLLAMA_MODEL"):
        model = os.environ["OLLAMA_MODEL"]
        for stage in ("title", "tags", "correction"):
            config["providers"][stage].setdefault("ollama_local", {})["model"] = model
        config["llm"]["model"] = model
    if os.environ.get("EDITOR"):
        config["editor"] = os.environ["EDITOR"]
    if os.environ.get("CAPTURE_METIS"):
        enabled = os.environ["CAPTURE_METIS"].lower() in ("true", "1", "yes")
        config["llm"]["enable_metis"] = enabled
        if not enabled:
            config["providers"]["tags"]["default"] = "disabled"
            config["providers"]["connections"]["default"] = "disabled"

    return config


def cfg() -> dict:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: dict) -> None:
    global _config
    _config = config


def get_stage_provider_name(stage: str, config: dict | None = None) -> str:
    config = config or cfg()
    return config["providers"][stage]["default"]


def get_stage_provider_config(stage: str, config: dict | None = None) -> dict:
    config = config or cfg()
    providers = config["providers"][stage]
    name = providers["default"]
    return providers.get(name, {})


def metis_enabled(config: dict | None = None) -> bool:
    config = config or cfg()
    if config["providers"]["tags"]["default"] == "disabled":
        return False
    return config["llm"].get("enable_metis", True)


def content_threshold(config: dict | None = None) -> int:
    config = config or cfg()
    return config["llm"].get("content_threshold", 30)
