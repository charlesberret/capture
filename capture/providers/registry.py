"""Provider registry — resolve per-stage backends from config."""

from __future__ import annotations

from capture.core.config import cfg, get_stage_provider_config, get_stage_provider_name


def get_provider(stage: str, provider_name: str | None = None, config: dict | None = None):
    config = config or cfg()
    name = provider_name or get_stage_provider_name(stage, config)
    provider_cfg = get_stage_provider_config(stage, config) if provider_name is None else config["providers"][stage].get(name, {})

    if stage == "transcription":
        return _transcription_provider(name, provider_cfg, config)
    if stage == "ocr":
        return _ocr_provider(name, provider_cfg)
    if stage == "title":
        return _title_provider(name, provider_cfg)
    if stage == "tags":
        return _tags_provider(name, provider_cfg)
    if stage == "correction":
        return _correction_provider(name, provider_cfg)
    if stage == "connections":
        return _connections_provider(name, provider_cfg, config)
    raise ValueError(f"Unknown pipeline stage: {stage}")


def _transcription_provider(name: str, provider_cfg: dict, config: dict):
    if name == "whisper_local":
        from capture.providers.transcription.whisper import WhisperProvider

        return WhisperProvider(provider_cfg, config)
    if name == "gemini_flash":
        from capture.providers.transcription.gemini import GeminiTranscriptionProvider

        return GeminiTranscriptionProvider(provider_cfg)
    if name == "disabled":
        from capture.providers.transcription.disabled import DisabledTranscriptionProvider

        return DisabledTranscriptionProvider()
    raise ValueError(f"Unknown transcription provider: {name}")


def _ocr_provider(name: str, provider_cfg: dict):
    if name == "apple_vision":
        from capture.providers.ocr.apple_vision import AppleVisionProvider

        return AppleVisionProvider(provider_cfg)
    if name == "tesseract":
        from capture.providers.ocr.tesseract import TesseractProvider

        return TesseractProvider(provider_cfg)
    if name == "disabled":
        from capture.providers.ocr.disabled import DisabledOCRProvider

        return DisabledOCRProvider()
    raise ValueError(f"Unknown OCR provider: {name}")


def _title_provider(name: str, provider_cfg: dict):
    if name == "ollama_local":
        from capture.providers.enrich.ollama import OllamaTitleProvider

        return OllamaTitleProvider(provider_cfg)
    if name == "gemini_flash":
        from capture.providers.enrich.gemini import GeminiTitleProvider

        return GeminiTitleProvider(provider_cfg)
    if name in ("truncate", "disabled"):
        from capture.providers.enrich.truncate import TruncateTitleProvider

        return TruncateTitleProvider()
    raise ValueError(f"Unknown title provider: {name}")


def _tags_provider(name: str, provider_cfg: dict):
    if name == "ollama_local":
        from capture.providers.enrich.ollama import OllamaTagsProvider

        return OllamaTagsProvider(provider_cfg)
    if name == "gemini_flash":
        from capture.providers.enrich.gemini import GeminiTagsProvider

        return GeminiTagsProvider(provider_cfg)
    if name == "disabled":
        from capture.providers.enrich.disabled import DisabledTagsProvider

        return DisabledTagsProvider()
    raise ValueError(f"Unknown tags provider: {name}")


def _correction_provider(name: str, provider_cfg: dict):
    if name == "ollama_local":
        from capture.providers.refine.ollama import OllamaCorrectionProvider

        return OllamaCorrectionProvider(provider_cfg)
    if name == "gemini_flash":
        from capture.providers.refine.gemini import GeminiCorrectionProvider

        return GeminiCorrectionProvider(provider_cfg)
    if name == "claude":
        from capture.providers.refine.claude import ClaudeCorrectionProvider

        return ClaudeCorrectionProvider(provider_cfg)
    if name == "disabled":
        from capture.providers.refine.disabled import DisabledCorrectionProvider

        return DisabledCorrectionProvider()
    raise ValueError(f"Unknown correction provider: {name}")


def _connections_provider(name: str, provider_cfg: dict, config: dict):
    if name == "keyword":
        from capture.providers.connections.keyword import KeywordConnectionsProvider

        return KeywordConnectionsProvider(provider_cfg, config)
    if name == "disabled":
        from capture.providers.connections.disabled import DisabledConnectionsProvider

        return DisabledConnectionsProvider()
    raise ValueError(f"Unknown connections provider: {name}")
