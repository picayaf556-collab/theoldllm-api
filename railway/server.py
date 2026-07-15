#!/usr/bin/env python3
"""Railway server - TheOldLLM OpenAI-compatible proxy."""

import asyncio
import json
import logging
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiohttp import web
from theoldllm.browser_client import PlaywrightTheOldLLM
from theoldllm.models import Models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("railway-server")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8080))
STORAGE_PATH = os.environ.get("STORAGE_PATH", "/app/data/session.json")

client = None
ready = False


async def get_client():
    global client, ready
    if client is None:
        client = PlaywrightTheOldLLM(
            base_url="https://theoldllm.vercel.app",
            headless=True,
            storage_path=STORAGE_PATH,
        )
    if not ready:
        logger.info("Starting Playwright browser...")
        try:
            await client._ensure_session()
            ready = True
            logger.info("Browser session established")
        except Exception as e:
            logger.error(f"Browser session failed: {e}")
            logger.error(traceback.format_exc())
            raise
    return client


async def chat_completions(request):
    try:
        cli = await get_client()
        body = await request.json()

        model_id = body.get("model", "gpt-5-mini-aichat")
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        max_tokens = body.get("max_tokens")
        temperature = body.get("temperature")
        top_p = body.get("top_p")

        logger.info(f"Chat: model={model_id}, stream={stream}, msgs={len(messages)}")

        if stream:
            resp = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                },
            )
            await resp.prepare(request)
            async for chunk in cli.chat_stream(model=model_id, messages=messages, max_tokens=max_tokens, temperature=temperature, top_p=top_p):
                await resp.write(_sse_chunk(chunk, model_id).encode())
                if chunk.is_done:
                    await resp.write(_sse_done(model_id).encode())
                    break
            return resp
        else:
            content = ""
            async for chunk in cli.chat_stream(model=model_id, messages=messages, max_tokens=max_tokens, temperature=temperature, top_p=top_p):
                if chunk.content:
                    content += chunk.content
            return web.json_response({
                "id": "chatcmpl-theoldllm",
                "object": "chat.completion",
                "created": _now(),
                "model": model_id,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        logger.exception("Chat error")
        return web.json_response({"error": {"message": str(e), "type": type(e).__name__}}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def list_models(request):
    seen = set()
    data = []
    for m in Models.ALL:
        if m.id not in seen:
            seen.add(m.id)
            data.append({"id": m.id, "object": "model", "created": 0, "owned_by": m.provider.value, "root": m.id})
    return web.json_response({"object": "list", "data": data}, headers={"Access-Control-Allow-Origin": "*"})


async def health(request):
    return web.json_response({"status": "ok" if ready else "starting", "model_count": len(Models.ALL)}, headers={"Access-Control-Allow-Origin": "*"})


async def cors(request):
    return web.Response(headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization"})


def _now():
    import time
    return int(time.time())


def _sse_chunk(chunk, model_id):
    d = {"id": "chatcmpl-theoldllm", "object": "chat.completion.chunk", "created": _now(), "model": model_id, "choices": [{"index": 0, "delta": {}, "finish_reason": None}]}
    delta = {}
    if chunk.content:
        delta["content"] = chunk.content
    if chunk.reasoning_content:
        delta["reasoning_content"] = chunk.reasoning_content
    if chunk.finish_reason:
        d["choices"][0]["finish_reason"] = chunk.finish_reason
    d["choices"][0]["delta"] = delta
    return f"data: {json.dumps(d)}\n\n"


def _sse_done(model_id):
    return f"data: {json.dumps({'id': 'chatcmpl-theoldllm', 'object': 'chat.completion.chunk', 'created': _now(), 'model': model_id, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"


async def main():
    app = web.Application()
    app.on_startup.append(lambda _: asyncio.create_task(_warmup()))
    app.router.add_post("/v1/chat/completions", chat_completions)
    app.router.add_get("/v1/models", list_models)
    app.router.add_get("/health", health)
    app.router.add_route("OPTIONS", "/v1/chat/completions", cors)
    app.router.add_route("OPTIONS", "/v1/models", cors)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()

    logger.info(f"Server ready on {HOST}:{PORT}")
    logger.info(f"OpenAI endpoint: http://{HOST}:{PORT}/v1")
    logger.info(f"Models: {len(Models.ALL)}")

    await asyncio.Event().wait()


async def _warmup():
    logger.info("Warming up browser session...")
    try:
        await get_client()
    except Exception as e:
        logger.warning(f"Warmup failed: {e}")
        logger.warning("Will retry on first request")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown")
