"""Talk to a local Ollama tag through the configured HTTP host.

The `ollama` CLI follows `OLLAMA_HOST`. That variable may point at a raw
daemon on a non-default port (for example `127.0.0.1:11435`) while an
admission proxy listens on `127.0.0.1:11434`. These stages POST
`/api/generate` at the configured host and never consult `OLLAMA_HOST`, so a
title or tag cannot slip past that proxy by inheriting the shell.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
from typing import NamedTuple

from capture.core.text import clean_model_output
from capture.providers._http import post_json

# Default is the fence, not the raw daemon. A config `host` may point elsewhere
# (a Mac's own Ollama); the environment variable must not.
FENCE_HOST = "http://127.0.0.1:11434"


class OllamaCompletion(NamedTuple):
    text: str | None
    error: str | None


def ollama_host(provider_cfg: dict) -> str:
    host = provider_cfg.get("host") or FENCE_HOST
    return str(host).rstrip("/")


_HTTP_STATUS = re.compile(r"HTTP\s+(\d{3})\b")


def _short_http_message(msg: str) -> str:
    """Status only. A long response body must not become the error string."""
    match = _HTTP_STATUS.search(msg)
    if match:
        return f"HTTP {match.group(1)}"
    collapsed = " ".join(msg.split())
    if collapsed and len(collapsed) <= 80:
        return collapsed
    return "HTTP error"


def _short_error(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, RuntimeError):
        msg = str(exc).strip()
        if msg.startswith("HTTP "):
            return _short_http_message(msg)
        return msg[:80] if msg else "request failed"
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, ConnectionRefusedError):
            return "connection refused"
        if reason is not None:
            return str(reason)[:80]
        return "connection error"
    if isinstance(exc, json.JSONDecodeError):
        return "malformed JSON"
    return type(exc).__name__


class _Joinable:
    """Stand-in for the old warmup Popen: `.wait(timeout=)` joins the thread.

    A timeout does not cancel the request. The load lives in the server; cutting
    the client short is what made the next call pay the cold start again.
    """

    def __init__(self, thread: threading.Thread):
        self._thread = thread

    def wait(self, timeout: int | None = None) -> None:
        self._thread.join(timeout=timeout)


def ollama_complete(provider_cfg: dict, prompt: str) -> OllamaCompletion:
    host = ollama_host(provider_cfg)
    model = provider_cfg.get("model", "qwen-capable")
    timeout = int(provider_cfg.get("timeout", 60))
    try:
        response = post_json(
            f"{host}/api/generate",
            {"model": model, "prompt": prompt, "stream": False},
            {"Content-Type": "application/json"},
            timeout=timeout,
        )
    except Exception as exc:
        return OllamaCompletion(None, _short_error(exc))
    text = response.get("response") if isinstance(response, dict) else None
    if not isinstance(text, str) or not text.strip():
        return OllamaCompletion(None, "empty response")
    return OllamaCompletion(clean_model_output(text), None)


def ollama_warmup(provider_cfg: dict) -> _Joinable:
    thread = threading.Thread(
        target=ollama_complete,
        args=(provider_cfg, "hi"),
        name="capture-ollama-warmup",
        daemon=False,
    )
    thread.start()
    return _Joinable(thread)
