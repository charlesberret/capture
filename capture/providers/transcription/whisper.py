"""Whisper local transcription provider."""

from __future__ import annotations

import subprocess
from pathlib import Path

from capture.core.vocabulary import apply_corrections, build_whisper_prompt

_whisper_model = None


class WhisperProvider:
    def __init__(self, provider_cfg: dict, config: dict):
        self.cfg = provider_cfg
        self.config = config

    def transcribe(self, audio_path: Path, *, hints: dict) -> str | None:
        vocab_by_topic = hints.get("vocab_by_topic", {})
        templates = hints.get("templates", {})
        corrections = hints.get("corrections", {})
        topic = hints.get("topic", "general")
        prompt = build_whisper_prompt(vocab_by_topic, templates, topic)

        backend = self.cfg.get("backend", "python")
        if backend == "cli":
            text = self._transcribe_cli(audio_path, prompt, corrections)
        else:
            text = self._transcribe_python(audio_path, prompt)
            if text:
                text = apply_corrections(text, corrections)
        return text

    def _transcribe_python(self, audio_path: Path, prompt: str | None) -> str | None:
        global _whisper_model
        try:
            import warnings

            warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
            if _whisper_model is None:
                import whisper

                model_name = self.cfg.get("model", "medium")
                print(f"  Loading Whisper model ({model_name})...")
                _whisper_model = whisper.load_model(model_name)

            kwargs = {
                "language": "en",
                "carry_initial_prompt": True,
                "verbose": False,
                "compression_ratio_threshold": 1.8,
            }
            if prompt:
                kwargs["initial_prompt"] = prompt
            result = _whisper_model.transcribe(str(audio_path), **kwargs)
            return result["text"].strip()
        except Exception as e:
            print(f"  Whisper Python API failed: {e}")
            return self._transcribe_cli(audio_path, prompt, {})

    def _transcribe_cli(self, audio_path: Path, prompt: str | None, corrections: dict) -> str | None:
        cmd = [
            "whisper",
            str(audio_path),
            "--model",
            self.cfg.get("model", "medium"),
            "--output_format",
            "txt",
            "--output_dir",
            "/tmp",
        ]
        if prompt:
            cmd.extend(["--initial_prompt", prompt])
        try:
            subprocess.run(cmd, capture_output=True, text=True)
            txt_file = Path("/tmp") / (audio_path.stem + ".txt")
            if txt_file.exists():
                text = txt_file.read_text().strip()
                txt_file.unlink()
                if text:
                    return apply_corrections(text, corrections)
        except Exception as e:
            print(f"  Whisper CLI failed: {e}")
        return None
