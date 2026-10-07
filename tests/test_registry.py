"""Provider registry: stage default, unknown names fail. No live backends."""

from __future__ import annotations

import pytest

from capture.providers.enrich.truncate import TruncateTitleProvider
from capture.providers.registry import get_provider
from tests.test_capture_floor import disabled_config


def test_get_provider_uses_the_stage_default(tmp_path):
    cfg = disabled_config(tmp_path)
    cfg["providers"]["title"]["default"] = "truncate"
    provider = get_provider("title", config=cfg)
    assert isinstance(provider, TruncateTitleProvider)


def test_unknown_stage_raises(tmp_path):
    with pytest.raises(KeyError):
        get_provider("not-a-stage", config=disabled_config(tmp_path))


def test_unknown_backend_raises(tmp_path):
    cfg = disabled_config(tmp_path)
    cfg["providers"]["title"]["default"] = "not-a-backend"
    with pytest.raises(ValueError, match="Unknown title provider"):
        get_provider("title", config=cfg)
