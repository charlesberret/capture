"""Gemini and Claude cloud providers: stub HTTP; no live API keys."""

from __future__ import annotations

import pytest

from capture.providers._http import claude_generate, gemini_generate
from capture.providers.enrich.gemini import GeminiTitleProvider
from capture.providers.refine.claude import ClaudeCorrectionProvider
from capture.providers.refine.gemini import GeminiCorrectionProvider


GEMINI_RESPONSE = {
    "candidates": [{"content": {"parts": [{"text": "A sensible title"}]}}]
}


def test_gemini_generate_sends_api_key_in_header_not_url(monkeypatch):
    seen = {}

    def fake_post(url, payload, headers, timeout=60):
        seen["url"] = url
        seen["headers"] = headers
        return GEMINI_RESPONSE

    monkeypatch.setattr("capture.providers._http.post_json", fake_post)
    out = gemini_generate(
        api_key="stub-key-not-real",
        model="gemini-2.0-flash",
        contents=[{"parts": [{"text": "hello"}]}],
    )
    assert out == "A sensible title"
    assert "key=" not in seen["url"]
    assert "?" not in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "stub-key-not-real"
    assert seen["headers"]["Content-Type"] == "application/json"
    assert seen["url"].endswith("gemini-2.0-flash:generateContent")


def test_gemini_title_returns_none_when_api_key_missing():
    provider = GeminiTitleProvider({"api_key": "env:GOOGLE_API_KEY_NOT_IN_TEST"})
    assert provider.generate("some note body") is None


def test_gemini_title_survives_http_error(monkeypatch):
    def fake_post(url, payload, headers, timeout=60):
        raise RuntimeError("HTTP 503: unavailable")

    monkeypatch.setattr("capture.providers._http.post_json", fake_post)
    monkeypatch.setattr(
        "capture.providers.enrich.gemini.format_prompt",
        lambda name, **kw: "title prompt",
    )
    provider = GeminiTitleProvider({"api_key": "stub-key-not-real"})
    assert provider.generate("note text") is None


def test_gemini_title_strips_title_prefix(monkeypatch):
    def fake_post(url, payload, headers, timeout=60):
        return {
            "candidates": [{"content": {"parts": [{"text": "title: From the prefix"}]}}]
        }

    monkeypatch.setattr("capture.providers._http.post_json", fake_post)
    monkeypatch.setattr(
        "capture.providers.enrich.gemini.format_prompt",
        lambda name, **kw: "title prompt",
    )
    provider = GeminiTitleProvider({"api_key": "stub-key-not-real"})
    assert provider.generate("note text") == "From the prefix"


def test_gemini_correction_keeps_text_on_http_error(monkeypatch):
    def fake_post(url, payload, headers, timeout=60):
        raise RuntimeError("HTTP 500: boom")

    monkeypatch.setattr("capture.providers._http.post_json", fake_post)
    monkeypatch.setattr(
        "capture.providers.refine.gemini.format_prompt",
        lambda name, **kw: "correct",
    )
    original = "Zimmerman"
    provider = GeminiCorrectionProvider({"api_key": "stub-key-not-real"})
    assert (
        provider.correct(original, source="audio", vocabulary="Zimmermann") == original
    )


def test_claude_generate_sends_api_key_header(monkeypatch):
    seen = {}

    def fake_post(url, payload, headers, timeout=60):
        seen["url"] = url
        seen["headers"] = headers
        return {"content": [{"type": "text", "text": "Zimmermann"}]}

    monkeypatch.setattr("capture.providers._http.post_json", fake_post)
    out = claude_generate(
        api_key="stub-key-not-real",
        model="claude-sonnet-4-20250514",
        prompt="fix this",
    )
    assert out == "Zimmermann"
    assert seen["headers"]["x-api-key"] == "stub-key-not-real"
    assert seen["url"] == "https://api.anthropic.com/v1/messages"


def test_claude_correction_applies_fix_when_length_ok(monkeypatch):
    def fake_post(url, payload, headers, timeout=60):
        return {"content": [{"type": "text", "text": "Zimmermann"}]}

    monkeypatch.setattr("capture.providers._http.post_json", fake_post)
    monkeypatch.setattr(
        "capture.providers.refine.claude.format_prompt",
        lambda name, **kw: "correct",
    )
    out = ClaudeCorrectionProvider({"api_key": "stub-key-not-real"}).correct(
        "Zimmerman", source="audio", vocabulary="Zimmermann"
    )
    assert out == "Zimmermann"
