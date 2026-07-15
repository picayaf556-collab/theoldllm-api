from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChatCompletionChunk:
    content: str = ""
    reasoning_content: Optional[str] = None
    finish_reason: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[dict] = None

    @property
    def is_done(self) -> bool:
        return self.finish_reason is not None


def parse_sse_line(line: str) -> Optional[ChatCompletionChunk]:
    """Parse a single SSE line from the API response."""
    if not line.startswith("data: "):
        return None

    data = line[6:].strip()

    if data == "[DONE]":
        return ChatCompletionChunk(finish_reason="stop")

    import json
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return None

    chunk = ChatCompletionChunk()

    choices = obj.get("choices", [])
    if not choices:
        return chunk

    delta = choices[0].get("delta", {})

    chunk.content = delta.get("content", "")
    chunk.reasoning_content = (
        delta.get("reasoning_content")
        or delta.get("thinking")
        or None
    )
    chunk.finish_reason = choices[0].get("finish_reason")
    chunk.model = obj.get("model")

    if "usage" in obj:
        chunk.usage = obj["usage"]

    return chunk
