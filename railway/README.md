# Deploy TheOldLLM Proxy on Railway

This deploys an OpenAI-compatible API proxy that routes through TheOldLLM.

## Deploy

### Option 1: One-click deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/xxx)

### Option 2: Manual deploy

1. Clone this repo
2. Connect your GitHub repo to Railway
3. Railway auto-detects the Dockerfile
4. Set environment variables (optional):
   - `PORT` - default 8080
   - `STORAGE_PATH` - session file path (default `/app/data/session.json`)

## Usage

Once deployed, configure opencode to use your Railway URL:

```json
{
  "provider": {
    "theoldllm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "TheOldLLM",
      "options": {
        "baseURL": "https://your-railway-app.up.railway.app/v1"
      },
      "models": {
        "gpt-5-mini-aichat": { "name": "GPT-5 Mini" },
        "claude-sonnet-5": { "name": "Claude Sonnet 5" },
        "gpt-5.5-thinking": { "name": "GPT-5.5 Thinking" }
      }
    }
  },
  "model": "theoldllm/gpt-5-mini-aichat"
}
```

## How it works

1. The server launches a headless Chromium browser via Playwright
2. It navigates to TheOldLLM and passes the Vercel Turnstile challenge
3. API requests are forwarded through this browser session
4. The session is cached to `/app/data/session.json`

## Notes

- First startup takes ~15-30 seconds (browser launch + Turnstile)
- The session refreshes automatically
- If the Turnstile challenge requires manual solving, Railway supports it via browser automation
- See health at `https://your-app.up.railway.app/health`
