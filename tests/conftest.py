"""Shared test fixtures."""

from __future__ import annotations

import subprocess

import pytest

import capture.core.pipeline as pipeline


@pytest.fixture(autouse=True)
def no_desktop_notifications(monkeypatch):
    """Keep `process` from posting a real macOS notification on every test run."""
    real_run = subprocess.run

    def run(args, *a, **kw):
        if args and args[0] == "osascript":
            return subprocess.CompletedProcess(args, 0, "", "")
        return real_run(args, *a, **kw)

    monkeypatch.setattr(pipeline.subprocess, "run", run)
