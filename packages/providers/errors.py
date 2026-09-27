"""Errors raised by decision providers."""


class ProviderError(RuntimeError):
    """Base class for provider failures."""


class ProviderTimeoutError(ProviderError):
    """The provider request timed out."""


class ProviderRateLimitError(ProviderError):
    """The provider rejected a request due to rate limiting."""


class ProviderResponseError(ProviderError):
    """The provider returned a malformed or unparseable response."""
