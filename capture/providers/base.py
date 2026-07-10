"""Shared provider exceptions."""

class ProviderError(Exception):
    pass

class ProviderUnavailable(ProviderError):
    pass
