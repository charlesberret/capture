"""Disabled correction provider — passthrough."""

class DisabledCorrectionProvider:
    def correct(self, text: str, *, source: str = "audio", vocabulary: str = "") -> str:
        return text
