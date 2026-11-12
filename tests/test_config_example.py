"""config.example.yaml must match MAC_PROVIDER_DEFAULTS for every provider value it sets."""

from __future__ import annotations

from pathlib import Path

import pytest

from capture.core.config import MAC_PROVIDER_DEFAULTS

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_PATH = REPO_ROOT / "config.example.yaml"


def _values_set_in_example(example: dict, defaults: dict, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], object, object]]:
    """Return (path, example_value, default_value) for each leaf set in example."""
    mismatches: list[tuple[tuple[str, ...], object, object]] = []
    for key, example_val in example.items():
        key_path = path + (key,)
        default_val = defaults.get(key)
        if isinstance(example_val, dict) and isinstance(default_val, dict):
            mismatches.extend(_values_set_in_example(example_val, default_val, key_path))
        elif example_val != default_val:
            mismatches.append((key_path, example_val, default_val))
    return mismatches


@pytest.fixture
def example_providers():
    yaml = pytest.importorskip("yaml")
    raw = yaml.safe_load(EXAMPLE_PATH.read_text()) or {}
    providers = raw.get("providers")
    assert providers is not None, "config.example.yaml must define providers:"
    return providers


def test_config_example_providers_match_mac_defaults(example_providers):
    mismatches = _values_set_in_example(example_providers, MAC_PROVIDER_DEFAULTS)
    if mismatches:
        lines = [
            f"  {'.'.join(p)}: example={ex!r}, default={df!r}"
            for p, ex, df in mismatches
        ]
        pytest.fail(
            "config.example.yaml provider values differ from MAC_PROVIDER_DEFAULTS:\n"
            + "\n".join(lines)
        )
