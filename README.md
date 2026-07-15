# TheOldLLM Python Client

Unofficial Python client for [TheOldLLM](https://theoldllm.vercel.app/) - a free multi-model AI chat service with access to GPT-5.6, Claude Sonnet 5, Gemini 3.5, Grok 4.5, and more.

## ⚠️ Important: Vercel WAF Limitation

TheOldLLM is deployed behind **Vercel's Web Application Firewall (WAF)** with a **Turnstile challenge**. Direct HTTP requests from Python (`requests`, `httpx`) are blocked.

**To use this API, you need one of these approaches:**
| Approach | Library | Requirements |
|----------|---------|-------------|
| **Browser-based** (recommended) | `PlaywrightTheOldLLM` | `playwright` + Chromium browser |
| **Direct requests** (limited) | `TheOldLLM` / `AsyncTheOldLLM` | Only works if you have a valid session cookie from a previous browser login |

## Installation

```bash
# For browser-based client (recommended)
pip install playwright
playwright install chromium

# For direct requests (try first)
pip install requests httpx
```

## Quick Start (Browser-Based)

```python
import asyncio
from theoldllm import PlaywrightTheOldLLM

async def main():
    async with PlaywrightTheOldLLM(headless=False) as client:
        result = await client.chat(
            model="gpt-5-mini-aichat",
            messages=[{"role": "user", "content": "Hello! What can you do?"}],
        )
        print(result)

asyncio.run(main())
```

> **First run:** A Chromium browser window will open and automatically pass the Vercel Turnstile challenge. After that, the session is cached.

## Streaming (Browser-Based)

```python
async for chunk in client.chat_stream(
    model="claude-sonnet-5",
    messages=[{"role": "user", "content": "Write a short poem"}],
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

## Session Persistence

```python
# Save session state to skip the challenge on next run
async with PlaywrightTheOldLLM(
    headless=True,
    storage_path="session.json",
) as client:
    ...
```

## Available Models

```python
from theoldllm import Models

for m in Models.ALL:
    print(f"  {m.id:35s} | {m.provider.value:10s} | {m.name}")
```

## Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `model` | str/Model | (required) | Model ID from `Models` |
| `messages` | list[dict] | (required) | `{"role": "user", "content": "..."}` |
| `max_tokens` | int | model default | Max output tokens |
| `reasoning_effort` | str | None | `"low"`, `"medium"`, `"high"`, `"max"` |
| `temperature` | float | 0.7 | Sampling temperature |
| `top_p` | float | 0.9 | Nucleus sampling |
| `frequency_penalty` | float | 0.0 | Frequency penalty |
| `presence_penalty` | float | 0.0 | Presence penalty |
| `web_search` | bool | False | Enable web search |

## Railway Deployment

Deploy the proxy on Railway so opencode can connect to it from anywhere:

### Prerequisites
- [Railway](https://railway.app) account
- GitHub repo with this project

### Deploy steps

1. Push this repo to GitHub
2. In Railway dashboard, click **New Project** → **Deploy from GitHub repo**
3. Select your repo
4. Railway auto-detects the `Dockerfile`
5. Wait for the build (~2-3 min first time)
6. Your app is live at `https://your-app.up.railway.app`

### Configure opencode

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "theoldllm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "TheOldLLM (hosted)",
      "options": {
        "baseURL": "https://your-app.up.railway.app/v1"
      },
      "models": {
        "gpt-5-mini-aichat": { "name": "GPT-5 Mini" },
        "gpt-5.5-thinking": { "name": "GPT-5.5 Thinking" },
        "claude-sonnet-5": { "name": "Claude Sonnet 5" },
        "gemini-3.5-flash": { "name": "Gemini 3.5 Flash" },
        "grok-4.3-latest": { "name": "Grok 4.3" }
      }
    }
  },
  "model": "theoldllm/gpt-5-mini-aichat"
}
```

Run `/connect` in opencode, select **Other**, enter `theoldllm` as provider ID (any dummy API key).

### Health check

Visit `https://your-app.up.railway.app/health` to check status.

### How it works on Railway

- A headless Chromium (Playwright) navigates to TheOldLLM
- It passes the Vercel Turnstile challenge automatically
- The browser session is cached to disk and reused across restarts
- OpenAI-compatible API is exposed on port 8080

> **Note:** The first startup launches a browser and takes ~15-30s. Subsequent requests are fast.

## Notes

- This is an **unofficial community client**.
- Frontier models (GPT-5.6, Claude Opus 4.8, etc.) require a signed-in account.
- The service has rate limits that apply per session.
- The browser-based approach uses Playwright to automate Chromium.
