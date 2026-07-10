"""HTTP helpers for cloud API providers."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def post_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def extract_gemini_text(response: dict) -> str | None:
    for candidate in response.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if "text" in p]
        joined = "".join(texts).strip()
        if joined:
            return joined
    return None


def gemini_generate(
    *,
    api_key: str,
    model: str,
    contents: list[dict],
    timeout: int = 60,
) -> str | None:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    response = post_json(
        url,
        {"contents": contents},
        {"Content-Type": "application/json"},
        timeout=timeout,
    )
    return extract_gemini_text(response)


def claude_generate(
    *,
    api_key: str,
    model: str,
    prompt: str,
    timeout: int = 60,
    max_tokens: int = 4096,
) -> str | None:
    response = post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=timeout,
    )
    for block in response.get("content", []):
        if block.get("type") == "text":
            text = block.get("text", "").strip()
            if text:
                return text
    return None
