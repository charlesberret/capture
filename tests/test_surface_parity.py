"""CLI vs iOS: copied prompts and provider-default tables stay identical."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

from capture.core.config import DEFAULTS, MAC_PROVIDER_DEFAULTS

REPO = Path(__file__).resolve().parents[1]
CLI_PROMPTS = REPO / "capture" / "core" / "prompts"
IOS_PROMPTS = REPO / "ios" / "Capture" / "Resources" / "Prompts"
PLATFORMS = REPO / "capture" / "platforms"
CAPTURE_MODELS = REPO / "ios" / "Capture" / "Sources" / "Models" / "CaptureModels.swift"

STAGE_ORDER = (
    "transcription",
    "ocr",
    "title",
    "tags",
    "correction",
    "connections",
)


def _load_platform_defaults(name: str) -> dict[str, str]:
    path = PLATFORMS / f"{name}.defaults.yaml"
    data = yaml.safe_load(path.read_text()) or {}
    providers = data.get("providers") or {}
    out: dict[str, str] = {}
    for stage in STAGE_ORDER:
        stage_cfg = providers.get(stage) or {}
        default = stage_cfg.get("default")
        assert default is not None, f"{path.name}: missing providers.{stage}.default"
        out[stage] = default
    return out


def _mac_defaults_from_config() -> dict[str, str]:
    return {stage: MAC_PROVIDER_DEFAULTS[stage]["default"] for stage in STAGE_ORDER}


def _parse_swift_stage_providers() -> dict[str, str]:
    text = CAPTURE_MODELS.read_text()
    match = re.search(
        r"static let stageProviders:.*?=\s*\[(.*?)\]",
        text,
        re.DOTALL,
    )
    assert match, "CaptureModels.swift: could not find ProviderDefaults.stageProviders"
    block = match.group(1)
    out: dict[str, str] = {}
    for stage in STAGE_ORDER:
        m = re.search(rf"\.{stage}:\s*\"([^\"]+)\"", block)
        assert m, f"CaptureModels.swift: missing stageProviders entry for .{stage}"
        out[stage] = m.group(1)
    return out


def _parse_swift_provider_defaults_literals() -> dict[str, object]:
    """Scalars in ProviderDefaults that mirror capture/core/config.py DEFAULTS."""
    text = CAPTURE_MODELS.read_text()
    patterns = {
        "geminiModel": r'static let geminiModel = "([^"]+)"',
        "contentThreshold": r"static let contentThreshold = (\d+)",
        "baseTags": r"static let baseTags = (\[[^\]]+\])",
        "serendipityAgeDays": r"static let serendipityAgeDays = (\d+)",
        "maxConnections": r"static let maxConnections = (\d+)",
        "maxKeywords": r"static let maxKeywords = (\d+)",
    }
    out: dict[str, object] = {}
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        assert m, f"CaptureModels.swift: missing ProviderDefaults.{key}"
        raw = m.group(1)
        if key == "baseTags":
            out[key] = ast.literal_eval(raw)
        elif key == "geminiModel":
            out[key] = raw
        else:
            out[key] = int(raw)
    return out


def _gemini_model_from_mac_defaults() -> str:
    return MAC_PROVIDER_DEFAULTS["title"]["gemini_flash"]["model"]


def test_prompt_files_match_between_cli_and_ios():
    cli_files = sorted(p.name for p in CLI_PROMPTS.glob("*.txt"))
    ios_files = sorted(p.name for p in IOS_PROMPTS.glob("*.txt"))
    assert cli_files, "expected prompt templates under capture/core/prompts"
    assert cli_files == ios_files, (
        "prompt filename sets differ "
        f"(cli={cli_files!r}, ios={ios_files!r})"
    )
    mismatches: list[str] = []
    for name in cli_files:
        cli_bytes = (CLI_PROMPTS / name).read_bytes()
        ios_bytes = (IOS_PROMPTS / name).read_bytes()
        if cli_bytes != ios_bytes:
            mismatches.append(name)
    assert not mismatches, f"prompt content differs: {', '.join(mismatches)}"


def test_mac_defaults_yaml_matches_config_provider_table():
    yaml_defaults = _load_platform_defaults("mac")
    config_defaults = _mac_defaults_from_config()
    assert yaml_defaults == config_defaults


def test_ios_defaults_yaml_matches_swift_stage_providers():
    yaml_defaults = _load_platform_defaults("ios")
    swift_defaults = _parse_swift_stage_providers()
    assert yaml_defaults == swift_defaults


def test_swift_provider_defaults_literals_match_python_defaults():
    swift = _parse_swift_provider_defaults_literals()
    assert swift["contentThreshold"] == DEFAULTS["llm"]["content_threshold"]
    assert swift["baseTags"] == DEFAULTS["defaults"]["tags"]
    assert swift["serendipityAgeDays"] == DEFAULTS["metis"]["serendipity_age_days"]
    assert swift["maxConnections"] == DEFAULTS["metis"]["max_connections"]
    assert swift["maxKeywords"] == DEFAULTS["metis"]["max_keywords"]
    assert swift["geminiModel"] == _gemini_model_from_mac_defaults()


@pytest.mark.parametrize("path", [CLI_PROMPTS, IOS_PROMPTS, PLATFORMS / "mac.defaults.yaml"])
def test_parity_sources_exist(path: Path):
    assert path.exists(), f"missing parity source: {path.relative_to(REPO)}"
