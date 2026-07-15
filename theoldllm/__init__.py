from .client import TheOldLLM, AsyncTheOldLLM
from .browser_client import PlaywrightTheOldLLM
from .models import Model, Provider, Models
from .exceptions import (
    TheOldLLMError,
    APIError,
    AuthenticationError,
    RateLimitError,
    StreamError,
)
from .streaming import ChatCompletionChunk

__version__ = "0.1.0"
__all__ = [
    "TheOldLLM",
    "AsyncTheOldLLM",
    "PlaywrightTheOldLLM",
    "Model",
    "Provider",
    "Models",
    "ChatCompletionChunk",
    "TheOldLLMError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "StreamError",
]
