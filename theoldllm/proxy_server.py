from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Optional

from .browser_client import PlaywrightTheOldLLM
from .client import BASE_URL
from .models import Models

logger = logging.getLogger("theoldllm-proxy")


class OpenAICompatProxy:
    """Local proxy that exposes TheOldLLM as an OpenAI-compatible API.

    opencode connects to this proxy as a custom OpenAI-compatible provider.
    The proxy uses Playwright to maintain a browser session that bypasses
    Vercel's WAF/Turnstile challenge.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11434,
        headless: bool = True,
        storage_path: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.headless = headless
        self.storage_path = storage_path or os.path.expanduser(
            "~/.local/share/theoldllm/session.json"
        )
        self._client: Optional[PlaywrightTheOldLLM] = None
        self._server = None

    async def _ensure_client(self):
        if self._client is None:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            self._client = PlaywrightTheOldLLM(
                base_url=BASE_URL,
                headless=self.headless,
                storage_path=self.storage_path,
            )
        await self._client._ensure_session()
        return self._client

    async def handle_chat_completions(self, body: dict):
        client = await self._ensure_client()

        model_id = body.get("model", "gpt-5-mini-aichat")
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        max_tokens = body.get("max_tokens")
        temperature = body.get("temperature")
        top_p = body.get("top_p")
        frequency_penalty = body.get("frequency_penalty")
        presence_penalty = body.get("presence_penalty")

        # Map reasoning_effort
        reasoning_effort = body.get("reasoning_effort")
        if not reasoning_effort and "reasoning_effort" in body.get("extra_body", {}):
            reasoning_effort = body["extra_body"]["reasoning_effort"]

        chunks = []
        async for chunk in client.chat_stream(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        ):
            chunks.append(chunk)
            if stream:
                yield _format_openai_chunk(chunk, model_id)
                if chunk.is_done:
                    yield _format_openai_done(model_id)
                    yield "\n"

        if not stream:
            full_content = "".join(c.content for c in chunks)
            yield json.dumps({
                "id": "chatcmpl-theoldllm",
                "object": "chat.completion",
                "created": int(asyncio.get_event_loop().time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": full_content,
                    },
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            })

    async def handle_models(self):
        models_list = []
        seen = set()
        for m in Models.ALL:
            if m.id not in seen:
                seen.add(m.id)
                models_list.append({
                    "id": m.id,
                    "object": "model",
                    "created": 0,
                    "owned_by": m.provider.value,
                    "permission": [],
                    "root": m.id,
                })
        return json.dumps({
            "object": "list",
            "data": models_list,
        })

    async def start(self):
        from aiohttp import web

        async def chat_handler(request):
            body = await request.json()
            stream = body.get("stream", False)

            if stream:
                response = web.StreamResponse(
                    status=200,
                    reason="OK",
                    headers={
                        "Content-Type": "text/event-stream",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
                await response.prepare(request)
                async for chunk in self.handle_chat_completions(body):
                    await response.write(chunk.encode())
                return response
            else:
                result = b""
                async for chunk in self.handle_chat_completions(body):
                    result += chunk.encode() if isinstance(chunk, str) else chunk
                return web.json_response(
                    status=200,
                    body=result,
                    headers={"Access-Control-Allow-Origin": "*"},
                )

        async def models_handler(request):
            data = await self.handle_models()
            return web.json_response(
                status=200,
                body=data,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        async def cors_preflight(request):
            return web.Response(
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                }
            )

        app = web.Application()
        app.router.add_post("/v1/chat/completions", chat_handler)
        app.router.add_get("/v1/models", models_handler)
        app.router.add_route("OPTIONS", "/v1/chat/completions", cors_preflight)
        app.router.add_route("OPTIONS", "/v1/models", cors_preflight)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(
            "TheOldLLM proxy running at http://%s:%d\n"
            "Configure opencode.json:\n"
            '  "provider": {\n'
            '    "theoldllm": {\n'
            '      "npm": "@ai-sdk/openai-compatible",\n'
            '      "name": "TheOldLLM",\n'
            '      "options": {\n'
            f'        "baseURL": "http://{self.host}:{self.port}/v1"\n'
            '      },\n'
            '      "models": {\n'
            f'        "gpt-5-mini-aichat": {{"name": "GPT-5 Mini"}}\n'
            '      }\n'
            '    }\n'
            '  },\n'
            f'  "model": "theoldllm/gpt-5-mini-aichat"',
            self.host, self.port,
        )

        self._server = runner

        # Keep running
        await asyncio.Event().wait()

    async def stop(self):
        if self._client:
            await self._client.close()
        if self._server:
            await self._server.cleanup()


def _format_openai_chunk(chunk, model_id: str) -> str:
    data = {
        "id": "chatcmpl-theoldllm",
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": model_id,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": None,
        }],
    }
    delta = {}
    if chunk.content:
        delta["content"] = chunk.content
    if chunk.reasoning_content:
        delta["reasoning_content"] = chunk.reasoning_content
    if chunk.finish_reason:
        data["choices"][0]["finish_reason"] = chunk.finish_reason

    data["choices"][0]["delta"] = delta
    return f"data: {json.dumps(data)}\n\n"


def _format_openai_done(model_id: str) -> str:
    data = {
        "id": "chatcmpl-theoldllm",
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": model_id,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }],
    }
    return f"data: {json.dumps(data)}\n\n"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="TheOldLLM OpenAI-compatible proxy for opencode")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=11434, help="Bind port (default: 11434)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless")
    parser.add_argument("--visible", action="store_true", help="Show browser window (debugging)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    proxy = OpenAICompatProxy(
        host=args.host,
        port=args.port,
        headless=not args.visible,
    )

    try:
        asyncio.run(proxy.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        asyncio.run(proxy.stop())


if __name__ == "__main__":
    main()
