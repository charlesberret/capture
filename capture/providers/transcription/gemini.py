"""Gemini Flash audio transcription provider."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from capture.core.config import resolve_secret
from capture.core.vocabulary import build_whisper_prompt
from capture.providers._http import gemini_generate


_MIME_MAP = {
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".caf": "audio/x-caf",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}


class GeminiTranscriptionProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def transcribe(self, audio_path: Path, *, hints: dict) -> str | None:
        api_key = resolve_secret(self.cfg.get("api_key"))
        if not api_key:
            print("  Gemini transcription: GOOGLE_API_KEY not set")
            return None

        suffix = audio_path.suffix.lower()
        mime = _MIME_MAP.get(suffix) or mimetypes.guess_type(str(audio_path))[0] or "audio/wav"
        audio_b64 = base64.b64encode(audio_path.read_bytes()).decode("ascii")

        vocab_by_topic = hints.get("vocab_by_topic", {})
        templates = hints.get("templates", {})
        topic = hints.get("topic", "general")
        vocab_hint = build_whisper_prompt(vocab_by_topic, templates, topic)
        hint_line = f"\nVocabulary context: {vocab_hint}" if vocab_hint else ""

        prompt = (
            "Transcribe this audio recording accurately. "
            "Return ONLY the transcription text, no commentary or labels."
            f"{hint_line}"
        )

        try:
            return gemini_generate(
                api_key=api_key,
                model=self.cfg.get("model", "gemini-2.0-flash"),
                contents=[
                    {
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime, "data": audio_b64}},
                        ]
                    }
                ],
                timeout=self.cfg.get("timeout", 120),
            )
        except Exception as e:
            print(f"  Gemini transcription failed: {e}")
            return None
