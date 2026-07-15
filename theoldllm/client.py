from __future__ import annotations

import json
import time
from typing import Any, Callable, Generator, Optional

import requests

from .exceptions import APIError, AuthenticationError, RateLimitError, StreamError
from .models import Model, Models, Provider
from .streaming import ChatCompletionChunk, parse_sse_line

BASE_URL = "https://theoldllm.vercel.app"
API_ENDPOINTS = {
    Provider.CHATGPT: "/api/chatgpt",
    Provider.AICHAT: "/api/aichat",
}
DEFAULT_TIMEOUT = 120


class TheOldLLM:
    def __init__(
        self,
        base_url: str = BASE_URL,
        supabase_token: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.supabase_token = supabase_token
        self.timeout = timeout
        self.session = session or requests.Session()

        self._default_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        }
        if self.supabase_token:
            headers["X-Supabase-Auth"] = self.supabase_token
        return headers

    def _resolve_provider(self, model: str | Model) -> tuple[str, Provider]:
        if isinstance(model, Model):
            return model.id, model.provider
        m = Models.by_id(model)
        if m:
            return m.id, m.provider
        return model, Provider.CHATGPT

    def _get_endpoint(self, provider: Provider) -> str:
        endpoint = API_ENDPOINTS.get(provider, "/api/chatgpt")
        return f"{self.base_url}{endpoint}"

    def _build_payload(
        self,
        model_id: str,
        messages: list[dict],
        provider: Provider,
        stream: bool = True,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        web_search: bool = False,
        upstream_provider: Optional[str] = None,
        thread_id: Optional[str] = None,
        **kwargs,
    ) -> dict:
        p = self._default_params.copy()
        if temperature is not None:
            p["temperature"] = temperature
        if top_p is not None:
            p["top_p"] = top_p
        if frequency_penalty is not None:
            p["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            p["presence_penalty"] = presence_penalty

        payload: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "stream": stream,
            **p,
        }

        m = Models.by_id(model_id)
        default_max = m.max_tokens if m else 8192
        payload["max_tokens"] = max_tokens or default_max

        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        if web_search:
            payload["webSearch"] = True

        if provider == Provider.AICHAT:
            if upstream_provider:
                payload["provider"] = upstream_provider
            elif m and m.upstream_provider:
                payload["provider"] = m.upstream_provider
            if thread_id:
                payload["threadId"] = thread_id

        payload.update(kwargs)
        return payload

    def _handle_error(self, response: requests.Response) -> None:
        status = response.status_code
        body = response.text

        try:
            err_data = response.json()
            err_msg = (
                err_data.get("error", {}).get("message")
                or err_data.get("error", "")
                or err_data.get("message", "")
            )
        except (json.JSONDecodeError, AttributeError):
            err_msg = body[:500] if body else f"HTTP {status}"

        if status == 401:
            raise AuthenticationError(err_msg, status_code=status, body=body)
        if status == 429 or status == 402:
            raise RateLimitError(err_msg, status_code=status, body=body)

        raise APIError(err_msg, status_code=status, body=body)

    # --- Sync Streaming ---

    def chat_stream(
        self,
        model: str | Model,
        messages: list[dict],
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        web_search: bool = False,
        **kwargs,
    ) -> Generator[ChatCompletionChunk, None, None]:
        model_id, provider = self._resolve_provider(model)
        endpoint = self._get_endpoint(provider)

        payload = self._build_payload(
            model_id=model_id,
            messages=messages,
            provider=provider,
            stream=True,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            web_search=web_search,
            **kwargs,
        )

        resp = self.session.post(
            endpoint,
            headers=self._get_headers(),
            json=payload,
            stream=True,
            timeout=self.timeout,
        )

        if not resp.ok:
            self._handle_error(resp)

        buffer = ""
        try:
            for raw_chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                if raw_chunk is None:
                    continue
                buffer += raw_chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    chunk = parse_sse_line(line)
                    if chunk is not None:
                        yield chunk
                        if chunk.is_done:
                            return
        except requests.exceptions.ChunkedEncodingError as e:
            raise StreamError(f"Stream interrupted: {e}") from e
        except requests.exceptions.RequestException as e:
            raise StreamError(f"Stream request failed: {e}") from e

    # --- Sync Non-Streaming ---

    def chat(
        self,
        model: str | Model,
        messages: list[dict],
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        web_search: bool = False,
        **kwargs,
    ) -> str:
        content_parts: list[str] = []
        for chunk in self.chat_stream(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            web_search=web_search,
            **kwargs,
        ):
            if chunk.content:
                content_parts.append(chunk.content)
        return "".join(content_parts)

    # --- Helper: format message ---

    @staticmethod
    def user_message(content: str) -> dict:
        return {"role": "user", "content": content}

    @staticmethod
    def assistant_message(content: str) -> dict:
        return {"role": "assistant", "content": content}

    @staticmethod
    def system_message(content: str) -> dict:
        return {"role": "system", "content": content}


class AsyncTheOldLLM:
    def __init__(
        self,
        base_url: str = BASE_URL,
        supabase_token: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.supabase_token = supabase_token
        self.timeout = timeout
        self._default_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        }
        if self.supabase_token:
            headers["X-Supabase-Auth"] = self.supabase_token
        return headers

    def _build_payload(self, **kwargs) -> dict:
        p = self._default_params.copy()
        overrides = {
            "temperature": kwargs.pop("temperature", None),
            "top_p": kwargs.pop("top_p", None),
            "frequency_penalty": kwargs.pop("frequency_penalty", None),
            "presence_penalty": kwargs.pop("presence_penalty", None),
        }
        for k, v in overrides.items():
            if v is not None:
                p[k] = v

        payload: dict[str, Any] = {
            "model": kwargs["model_id"],
            "messages": kwargs["messages"],
            "stream": kwargs.get("stream", True),
            **p,
        }

        m = Models.by_id(kwargs["model_id"])
        default_max = m.max_tokens if m else 8192
        payload["max_tokens"] = kwargs.get("max_tokens") or default_max

        if kwargs.get("reasoning_effort"):
            payload["reasoning_effort"] = kwargs["reasoning_effort"]
        if kwargs.get("web_search"):
            payload["webSearch"] = True

        provider = kwargs.get("provider")
        if provider == Provider.AICHAT:
            upstream = kwargs.get("upstream_provider") or (m and m.upstream_provider)
            if upstream:
                payload["provider"] = upstream

        return payload

    async def chat_stream(
        self,
        model: str | Model,
        messages: list[dict],
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        web_search: bool = False,
        **kwargs,
    ):
        import httpx

        model_id, provider = (
            (model.id, model.provider) if isinstance(model, Model)
            else (model, Provider.CHATGPT)
        )
        m = Models.by_id(model_id)
        if m:
            provider = m.provider

        endpoint = API_ENDPOINTS.get(provider, "/api/chatgpt")
        url = f"{self.base_url}{endpoint}"

        payload = self._build_payload(
            model_id=model_id,
            messages=messages,
            provider=provider,
            stream=True,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            web_search=web_search,
            upstream_provider=kwargs.pop("upstream_provider", None),
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                url,
                headers=self._get_headers(),
                json=payload,
            ) as resp:
                if not resp.is_success:
                    body = await resp.aread()
                    err_text = body.decode() if body else ""
                    if resp.status_code == 429:
                        raise RateLimitError(err_text, status_code=resp.status_code)
                    raise APIError(err_text, status_code=resp.status_code)

                buffer = ""
                async for raw_chunk in resp.aiter_text():
                    buffer += raw_chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        chunk = parse_sse_line(line)
                        if chunk is not None:
                            yield chunk
                            if chunk.is_done:
                                return

    async def chat(
        self,
        model: str | Model,
        messages: list[dict],
        **kwargs,
    ) -> str:
        parts: list[str] = []
        async for chunk in self.chat_stream(model=model, messages=messages, **kwargs):
            if chunk.content:
                parts.append(chunk.content)
        return "".join(parts)

    @staticmethod
    def user_message(content: str) -> dict:
        return {"role": "user", "content": content}

    @staticmethod
    def assistant_message(content: str) -> dict:
        return {"role": "assistant", "content": content}

    @staticmethod
    def system_message(content: str) -> dict:
        return {"role": "system", "content": content}
