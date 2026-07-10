"""Disabled transcription — returns None."""

from pathlib import Path


class DisabledTranscriptionProvider:
    def transcribe(self, audio_path: Path, *, hints: dict) -> str | None:
        return None
