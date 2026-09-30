"""Talk to a local Ollama tag through the configured HTTP host.

The `ollama` CLI follows `OLLAMA_HOST`. On the GPU host that variable points at
the raw daemon (`127.0.0.1:11435`). The admission clerk is the tinpusher fence
on `127.0.0.1:11434` (`gpu-admit` via `tinpusher-proxy`). These stages POST
`/api/generate` at the configured host and never consult `OLLAMA_HOST`, so a
title or tag cannot slip past the fence by inheriting the shell.
"""

from __future__ import annotations

import threading

from capture.core.text import clean_model_output
from capture.providers._http import post_json

# Default is the fence, not the raw daemon. A config `host` may point elsewhere
# (a Mac's own Ollama); the environment variable must not.
FENCE_HOST = "http://127.0.0.1:11434"


def ollama_host(provider_cfg: dict) -> str:
    host = provider_cfg.get("host") or FENCE_HOST
    return str(host).rstrip("/")


class _Joinable:
    """Stand-in for the old warmup Popen: `.wait(timeout=)` joins the thread.

    A timeout does not cancel the request. The load lives in the server; cutting
    the client short is what made the next call pay the cold start again.
    """

    def __init__(self, thread: threading.Thread):
        self._thread = thread

    def wait(self, timeout: int | None = None) -> None:
        self._thread.join(timeout=timeout)


def ollama_complete(provider_cfg: dict, prompt: str) -> str | None:
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
    except Exception:
        return None
    text = response.get("response") if isinstance(response, dict) else None
    if not isinstance(text, str) or not text.strip():
        return None
    return clean_model_output(text)


def ollama_warmup(provider_cfg: dict) -> _Joinable:
    thread = threading.Thread(
        target=ollama_complete,
        args=(provider_cfg, "hi"),
        name="capture-ollama-warmup",
        daemon=False,
    )
    thread.start()
    return _Joinable(thread)
