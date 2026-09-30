"""Local Ollama stages knock the configured host, never OLLAMA_HOST.

On the GPU host OLLAMA_HOST is the raw daemon (:11435). The fence is :11434.
These tests stub the HTTP call; they do not start Ollama.
"""

from __future__ import annotations

import os

import pytest

from capture.providers.enrich.ollama import OllamaTagsProvider, OllamaTitleProvider
from capture.providers.ollama_http import FENCE_HOST, ollama_complete, ollama_host
from capture.providers.refine.ollama import OllamaCorrectionProvider


@pytest.fixture(autouse=True)
def raw_daemon_in_the_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11435")


def test_builtin_config_host_ignores_ollama_host(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("notes_dir: ~/Notes\nproviders:\n  title:\n    default: ollama_local\n")
    monkeypatch.setenv("CAPTURE_CONFIG", str(path))
    from capture.core.config import load_config

    loaded = load_config(path)
    for stage in ("title", "tags", "correction"):
        assert loaded["providers"][stage]["ollama_local"]["host"] == FENCE_HOST


def test_default_host_is_the_fence_not_the_environment():
    assert ollama_host({}) == FENCE_HOST
    assert ":11435" not in ollama_host({})
    assert os.environ["OLLAMA_HOST"].endswith(":11435")


def test_complete_posts_generate_to_the_fence(monkeypatch):
    seen = {}

    def fake_post(url, payload, headers, timeout=60):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return {"response": "A fenced title"}

    monkeypatch.setattr("capture.providers.ollama_http.post_json", fake_post)
    text = ollama_complete({"model": "ornith:9b", "timeout": 12}, "prompt")
    assert text == "A fenced title"
    assert seen["url"] == "http://127.0.0.1:11434/api/generate"
    assert seen["payload"]["model"] == "ornith:9b"
    assert seen["payload"]["stream"] is False
    assert seen["timeout"] == 12


def test_explicit_host_is_honored_and_env_is_not(monkeypatch):
    seen = {}

    def fake_post(url, payload, headers, timeout=60):
        seen["url"] = url
        return {"response": "ok"}

    monkeypatch.setattr("capture.providers.ollama_http.post_json", fake_post)
    ollama_complete({"host": "http://127.0.0.1:11434/"}, "p")
    assert seen["url"] == "http://127.0.0.1:11434/api/generate"


def test_title_and_tags_do_not_shell_out(monkeypatch):
    calls = []

    def fake_post(url, payload, headers, timeout=60):
        calls.append((url, payload["prompt"]))
        if payload["prompt"].startswith("tags-prompt"):
            return {"response": "kernel, fence"}
        return {"response": "Short Fenced Title"}

    monkeypatch.setattr("capture.providers.ollama_http.post_json", fake_post)
    monkeypatch.setattr(
        "capture.providers.enrich.ollama.format_prompt",
        lambda name, **kw: f"{name}-prompt",
    )

    def boom(*args, **kwargs):
        raise AssertionError("ollama CLI must not run")

    monkeypatch.setattr("subprocess.run", boom)
    monkeypatch.setattr("subprocess.Popen", boom)

    cfg = {"model": "qwen-capable", "timeout": 5}
    title = OllamaTitleProvider(cfg).generate("a captured thought about fences")
    tags = OllamaTagsProvider(cfg).suggest("a captured thought about fences")
    assert title == "Short Fenced Title"
    assert tags == ["kernel", "fence"]
    assert calls
    assert all(url.startswith(FENCE_HOST) for url, _prompt in calls)


def test_correction_uses_the_same_fence(monkeypatch):
    seen = {}

    def fake_post(url, payload, headers, timeout=60):
        seen["url"] = url
        return {"response": "Zimmermann"}

    monkeypatch.setattr("capture.providers.ollama_http.post_json", fake_post)
    monkeypatch.setattr(
        "capture.providers.refine.ollama.format_prompt",
        lambda name, **kw: "correct",
    )
    out = OllamaCorrectionProvider({"timeout": 5}).correct(
        "Zimmerman", source="audio", vocabulary="Zimmermann"
    )
    assert out == "Zimmermann"
    assert seen["url"] == f"{FENCE_HOST}/api/generate"
