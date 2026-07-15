#!/usr/bin/env python3
"""Railway server - TheOldLLM OpenAI-compatible proxy."""

import asyncio
import json
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiohttp import web
from theoldllm.browser_client import PlaywrightTheOldLLM
from theoldllm.models import Models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("railway-server")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8080))
STORAGE_PATH = os.environ.get("STORAGE_PATH", "/app/data/session.json")

client: PlaywrightTheOldLLM | None = None


async def get_client() -> PlaywrightTheOldLLM:
    global client
    if client is None:
        client = PlaywrightTheOldLLM(
            base_url="https://theoldllm.vercel.app",
            headless=True,
            storage_path=STORAGE_PATH,
        )
        logger.info("Starting Playwright browser and navigating to TheOldLLM...")
        await client._ensure_session()
        logger.info("Browser session established successfully")
    return client


async def chat_completions(request: web.Request) -> web.Response:
    try:
        cli = await get_client()
        body = await request.json()

        model_id = body.get("model", "gpt-5-mini-aichat")
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        max_tokens = body.get("max_tokens")
        temperature = body.get("temperature")
        top_p = body.get("top_p")

        logger.info(f"Request: model={model_id}, stream={stream}, messages={len(messages)}")

        if stream:
            response = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                },
            )
            await response.prepare(request)

            async for chunk in cli.chat_stream(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ):
                sse_data = _format_openai_chunk(chunk, model_id)
                await response.write(sse_data.encode())
                if chunk.is_done:
                    await response.write(_format_openai_done(model_id).encode())
                    break

            return response
        else:
            full_content = ""
            async for chunk in cli.chat_stream(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ):
                if chunk.content:
                    full_content += chunk.content

            result = json.dumps({
                "id": "chatcmpl-theoldllm",
                "object": "chat.completion",
                "created": int(asyncio.get_event_loop().time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": full_content},
                    "finish_reason": "stop",
                }],
            })
            return web.json_response(body=result, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        logger.exception("Error handling chat request")
        return web.json_response(
            {"error": {"message": str(e), "type": type(e).__name__}},
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )


async def list_models(request: web.Request) -> web.Response:
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
                "root": m.id,
            })

    return web.json_response({
        "object": "list",
        "data": models_list,
    }, headers={"Access-Control-Allow-Origin": "*"})


async def cors_preflight(request: web.Request) -> web.Response:
    return web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )


async def health_check(request: web.Request) -> web.Response:
    status = "ok" if client and client._session_ready.is_set() else "starting"
    return web.json_response({"status": status, "model_count": len(Models.ALL)})


async def startup():
    logger.info(f"Server starting on {HOST}:{PORT}")
    try:
        cli = await get_client()
        logger.info("Initial browser session established")
    except Exception as e:
        logger.error(f"Failed to establish initial browser session: {e}")
        logger.warning("Server will retry on first request")


def _format_openai_chunk(chunk, model_id):
    import time
    data = {
        "id": "chatcmpl-theoldllm",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_id,
        "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
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


def _format_openai_done(model_id):
    import time
    data = {
        "id": "chatcmpl-theoldllm",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_id,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    return f"data: {json.dumps(data)}\n\n"


async def main():
    app = web.Application()
    app.on_startup.append(lambda _: asyncio.create_task(startup()))
    app.router.add_post("/v1/chat/completions", chat_completions)
    app.router.add_get("/v1/models", list_models)
    app.router.add_get("/health", health_check)
    app.router.add_route("OPTIONS", "/v1/chat/completions", cors_preflight)
    app.router.add_route("OPTIONS", "/v1/models", cors_preflight)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()

    logger.info(f"Server ready at http://{HOST}:{PORT}")
    logger.info(f"OpenAI-compatible endpoint: http://{HOST}:{PORT}/v1")
    logger.info(f"Models available: {len(Models.ALL)}")

    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
