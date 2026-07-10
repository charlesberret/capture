"""Disabled tags provider."""

class DisabledTagsProvider:
    def suggest(self, content: str, warmup=None) -> list[str]:
        return []
