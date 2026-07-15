from theoldllm import TheOldLLM, AsyncTheOldLLM, Models
import asyncio


def sync_example():
    client = TheOldLLM()

    print("=== Sync Streaming Example ===")
    print("Model: gpt-5-mini-aichat")
    print("Streaming response:\n")

    for chunk in client.chat_stream(
        model="gpt-5-mini-aichat",
        messages=[
            TheOldLLM.system_message("You are a helpful assistant."),
            TheOldLLM.user_message("Tell me 3 interesting facts about space."),
        ],
        max_tokens=512,
    ):
        if chunk.content:
            print(chunk.content, end="", flush=True)
        if chunk.reasoning_content:
            pass  # print(f"<thinking>{chunk.reasoning_content}</thinking>\n", end="")

    print("\n\n=== Non-Streaming Example ===")
    response = client.chat(
        model="gpt-5-mini-aichat",
        messages=[{"role": "user", "content": "What is 2+2?"}],
    )
    print(f"Response: {response}")


async def async_example():
    client = AsyncTheOldLLM()

    print("=== Async Streaming ===")
    async for chunk in client.chat_stream(
        model="claude-sonnet-5",
        messages=[{"role": "user", "content": "Write a haiku about coding"}],
        max_tokens=256,
    ):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print()


def list_models():
    print("=== Available Models ===")
    for m in Models.ALL:
        print(f"  {m.id:35s} | {m.provider.value:10s} | {m.name}")
    print(f"\nTotal: {len(Models.ALL)} models")


if __name__ == "__main__":
    list_models()
    print()
    sync_example()
    print()
    asyncio.run(async_example())
