from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Provider(Enum):
    CHATGPT = "chatgpt"
    AICHAT = "aichat"
    ENHANCED = "p1"
    STANDARD = "p2"
    CLOUD = "p3"
    PREMIUM = "p4"
    UNIVERSAL = "p7"
    OLDLLM = "p9"
    BLAZEAI = "p13"


@dataclass
class Model:
    id: str
    name: str
    provider: Provider
    supports_streaming: bool = True
    supports_reasoning: bool = False
    supports_images: bool = False
    supports_search: bool = False
    max_tokens: int = 8192
    description: str = ""
    upstream_model: Optional[str] = None
    upstream_provider: Optional[str] = None


class Models:
    ALL: list[Model] = []

    @classmethod
    def by_id(cls, model_id: str) -> Optional[Model]:
        for m in cls.ALL:
            if m.id == model_id:
                return m
        return None

    @classmethod
    def by_provider(cls, provider: Provider) -> list[Model]:
        return [m for m in cls.ALL if m.provider == provider]

    @classmethod
    def list_ids(cls) -> list[str]:
        return [m.id for m in cls.ALL]


Models.ALL = [
    # --- AIChat Bridge ---
    Model("claude-sonnet-5", "Claude Sonnet 5", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="claude-sonnet-5", upstream_provider="anthropic"),
    Model("claude-opus-4-8", "Claude Opus 4.8", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="claude-opus-4-8", upstream_provider="anthropic"),
    Model("claude-opus-4-7", "Claude Opus 4.7", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="claude-opus-4-7", upstream_provider="anthropic"),
    Model("claude-fable-5", "Claude Fable 5", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="claude-fable-5", upstream_provider="anthropic"),
    Model("gpt-5.6-sol", "GPT-5.6 Sol", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="gpt-5.6-sol", upstream_provider="openai"),
    Model("gpt-5.6-terra", "GPT-5.6 Terra", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="gpt-5.6-terra", upstream_provider="openai"),
    Model("gpt-5.6-luna", "GPT-5.6 Luna", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="gpt-5.6-luna", upstream_provider="openai"),
    Model("gpt-5.5-thinking", "GPT-5.5 Thinking", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="gpt-5.5-thinking", upstream_provider="openai"),
    Model("gpt-5-mini-aichat", "GPT-5 Mini", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="gpt-5-mini-aichat", upstream_provider="openai"),
    Model("gemini-3.1-pro", "Gemini 3.1 Pro", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="gemini-3.1-pro", upstream_provider="google"),
    Model("gemini-3.5-flash", "Gemini 3.5 Flash", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="gemini-3.5-flash", upstream_provider="google"),
    Model("grok-4.5-latest", "Grok 4.5", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="grok-4.5-latest", upstream_provider="xai"),
    Model("grok-4.3-latest", "Grok 4.3", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="grok-4.3-latest", upstream_provider="xai"),
    Model("grok-4.2-latest", "Grok 4.2", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="grok-4.2-latest", upstream_provider="xai"),
    Model("grok-4.1-latest", "Grok 4.1", Provider.AICHAT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536,
          upstream_model="grok-4.1-latest", upstream_provider="xai"),

    # --- ChatGPT/OpenRouter provider ---
    Model("gpt-5.4", "GPT-5.4", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("gpt-5.3", "GPT-5.3", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("gpt-5.2", "GPT-5.2", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("gpt-5.1", "GPT-5.1", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("o4-mini", "o4-mini", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("o3", "o3", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("o3-mini", "o3-mini", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("gpt-4o", "GPT-4o", Provider.CHATGPT,
          supports_streaming=True, max_tokens=16384),
    Model("gpt-4o-mini", "GPT-4o Mini", Provider.CHATGPT,
          supports_streaming=True, max_tokens=16384),
    Model("gemini-2.5-pro", "Gemini 2.5 Pro", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("gemini-2.5-flash", "Gemini 2.5 Flash", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("gemini-2.0-flash-001", "Gemini 2.0 Flash", Provider.CHATGPT,
          supports_streaming=True, max_tokens=16384),
    Model("claude-sonnet-4.5", "Claude Sonnet 4.5", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("claude-haiku-4.5", "Claude Haiku 4.5", Provider.CHATGPT,
          supports_streaming=True, max_tokens=16384),
    Model("claude-opus-4.5", "Claude Opus 4.5", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("llama-4-maverick", "Llama 4 Maverick", Provider.CHATGPT,
          supports_streaming=True, max_tokens=16384),
    Model("deepseek-v3", "DeepSeek V3", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("deepseek-r1", "DeepSeek R1", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("grok-4", "Grok 4", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("grok-3", "Grok 3", Provider.CHATGPT,
          supports_streaming=True, supports_reasoning=True, max_tokens=65536),
    Model("sonar-pro", "Sonar Pro", Provider.CHATGPT,
          supports_streaming=True, supports_search=True, max_tokens=16384),
    Model("sonar-deep-research", "Sonar Deep Research", Provider.CHATGPT,
          supports_streaming=True, supports_search=True, max_tokens=16384),
]
