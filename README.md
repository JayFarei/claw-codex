# Claw Codex OpenRouter Mock

Local FastAPI server that authenticates with OpenAI Codex OAuth (ChatGPT subscription) and exposes an OpenRouter-like `/v1/chat/completions` endpoint for a model called `claw/codex`.

This is intended for local testing and investigation. Make sure your usage complies with provider terms.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
claw-codex
```

The OAuth redirect URI is fixed to `http://localhost:1455/auth/callback`, so the server should run on port `1455`.

Open the demo UI at:

```
http://127.0.0.1:1455/demo
```

## OAuth flow

Start login:

```bash
curl -s -X POST http://127.0.0.1:1455/auth/codex/start | python -m json.tool
```

Open the `authorize_url` in a browser, log in, and you should see a success page. Tokens are stored in `~/.claw-codex/auth.json`.

If the callback cannot reach the server, copy the redirect URL from the browser and exchange manually:

```bash
curl -s -X POST http://127.0.0.1:1455/auth/codex/exchange \
  -H 'content-type: application/json' \
  -d '{"code": "PASTE_REDIRECT_URL_OR_CODE"}' | python -m json.tool
```

## OpenRouter-style request

```bash
curl -s http://127.0.0.1:1455/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "claw/codex",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Say hello from Codex."}
    ],
    "stream": false
  }' | python -m json.tool
```

## Notes

- `claw/codex` is mapped to the Codex model ID from `CLAW_CODEX_MODEL` (default `gpt-5.2`).
- The server stores credentials in `~/.claw-codex/auth.json` unless overridden with `CLAW_CODEX_AUTH_FILE`.
- Streaming is supported with `"stream": true`, but only text deltas are emitted (tool calls are ignored).

## Test mode (no real OAuth)

Set `CLAW_CODEX_MOCK=1` to bypass real OAuth and Codex calls (useful for e2e tests).

Run tests:

```bash
pip install -e '.[dev]'
pytest
```
