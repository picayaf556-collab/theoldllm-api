"""Test script to verify API connectivity."""
import requests

s = requests.Session()

# First visit the homepage
r1 = s.get(
    "https://theoldllm.vercel.app/",
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    },
)
print(f"Homepage status: {r1.status_code}")
print(f"Cookies: {dict(s.cookies)}")

# Now try the API
url = "https://theoldllm.vercel.app/api/chatgpt"
headers = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Origin": "https://theoldllm.vercel.app",
    "Referer": "https://theoldllm.vercel.app/",
    "Accept": "text/event-stream",
    "Accept-Language": "en-US,en;q=0.9",
}

body = {
    "model": "gpt-5-mini-aichat",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "stream": True,
    "max_tokens": 50,
    "temperature": 0.7,
    "top_p": 0.9,
}

resp = s.post(url, headers=headers, json=body, stream=True, timeout=30)
print(f"\nAPI Status: {resp.status_code}")
print(f"API Headers: {dict(resp.headers)}")

if resp.status_code == 429:
    print(f"\nBlocked by security. Body preview: {resp.text[:1000]}")
elif resp.ok:
    print("\nResponse stream:")
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                print("\n[DONE]")
                break
            print(data)
else:
    print(f"\nError body: {resp.text[:1000]}")
