from capture.providers.registry import get_provider


def test_model_and_media_providers_are_disabled(disabled_provider_config, tmp_path):
    assert get_provider("title").generate("A local title") == "A local title"
    assert get_provider("tags").suggest("No remote tags") == []
    assert get_provider("ocr").extract(tmp_path / "capture.png") is None
    assert (
        get_provider("transcription").transcribe(
            tmp_path / "capture.wav",
            hints={},
        )
        is None
    )
