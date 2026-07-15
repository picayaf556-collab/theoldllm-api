class TheOldLLMError(Exception):
    """Base exception for TheOldLLM API errors."""


class APIError(TheOldLLMError):
    """Raised when the API returns an unexpected error."""

    def __init__(self, message="API error", status_code=None, body=None):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class AuthenticationError(TheOldLLMError):
    """Raised when authentication fails."""

    def __init__(self, message="Authentication failed", status_code=None, body=None):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class RateLimitError(TheOldLLMError):
    """Raised when rate limited or quota exceeded."""

    def __init__(self, message="Rate limited", status_code=None, body=None):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class StreamError(TheOldLLMError):
    """Raised when a stream fails or is interrupted."""
