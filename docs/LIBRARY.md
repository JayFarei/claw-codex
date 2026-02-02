# Library Usage

`claw_codex` now supports direct library integration so other projects can call Codex without running the proxy server.

## Main API

- Sync client: `claw_codex.ClawCodexClient`
- Async client: `claw_codex.AsyncClawCodexClient`

Both clients use the same OAuth credential store (`~/.claw-codex/auth.json` by default).

## Authentication Flow

```python
from claw_codex import ClawCodexClient

client = ClawCodexClient()
start = client.start_auth()
print(start.authorize_url)
client.exchange_code("PASTE_REDIRECT_URL_OR_CODE")
```

You can also authenticate via CLI:

```bash
claw-codex auth login --open-browser
```

or UI (`claw-codex serve` then `http://127.0.0.1:1455/demo`).

## Chat Completions

```python
response = client.chat_completions(
    model="claw/codex",
    messages=[
        {"role": "system", "content": "You are concise."},
        {"role": "user", "content": "Summarize this in one sentence."},
    ],
)
print(response["choices"][0]["message"]["content"])
```

Accepted model aliases:

- `claw/codex`
- `claw/codex-responses`
- `openai-codex`

## Async Streaming

```python
import asyncio
from claw_codex import AsyncClawCodexClient

async def main():
    client = AsyncClawCodexClient()
    async for chunk in client.stream_chat_completions(
        model="claw/codex",
        messages=[{"role": "user", "content": "Stream hello"}],
    ):
        delta = chunk["choices"][0]["delta"].get("content")
        if delta:
            print(delta, end="")

asyncio.run(main())
```

## Mock Mode for Tests

Set `CLAW_CODEX_MOCK=1` or initialize clients with `mock_mode=True`.
