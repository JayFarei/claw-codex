# Claw Codex Python Library + Local Server

Local tools for using Codex OAuth credentials (ChatGPT subscription) in two ways:

- **As a reusable library** for direct `chat.completions`-style calls.
- **As a local FastAPI server** with OpenRouter-like endpoints and a demo UI.

> This project is for local testing/investigation. Make sure usage complies with provider terms.

## Install

```bash
pip install claw-codex
```

For local development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Library Quickstart

```python
from claw_codex import ClawCodexClient

client = ClawCodexClient()

# One-time auth flow
start = client.start_auth()
print(start.authorize_url)
client.exchange_code("PASTE_REDIRECT_URL_OR_CODE")

# OpenRouter-style chat call
resp = client.chat_completions(
    model="claw/codex",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Say hello from Codex."},
    ],
)
print(resp["choices"][0]["message"]["content"])
```

## Dynamic Redirect URI Integration

For downstream applications that need to redirect users back to their own callback URL after OAuth authentication, this library supports encoding the actual redirect URI in the OAuth state parameter.

### How It Works

1. **Library's registered redirect**: The OAuth authorization URL always uses the library's registered redirect URI (`http://localhost:1455/auth/callback`)
2. **State encoding**: When you provide a custom `redirect_uri`, it's base64-encoded into the OAuth state parameter
3. **Callback handling**: When OpenAI redirects back to the library's callback, the library decodes the state to extract your actual redirect URI
4. **Token exchange**: The library uses your actual redirect URI when exchanging the code for tokens

This approach works because OpenAI only validates the `redirect_uri` parameter during token exchange, not during the callback.

### Usage for Downstream Apps

```python
from claw_codex import ClawCodexClient

client = ClawCodexClient()

# Start auth with your custom redirect URI
# This will redirect back to your app after OAuth
auth = client.start_auth(
    redirect_uri="http://localhost:8001/api/settings/codex/callback"
)

# Redirect your user to auth.authorize_url
# After authentication, OpenAI will redirect to:
# http://localhost:1455/auth/callback?code=...&state=...
# 
# The library's callback will decode the state and use your redirect URI
# for the token exchange

# Exchange the code (the library automatically uses the correct redirect_uri)
creds = client.exchange_code("PASTE_REDIRECT_URL_OR_CODE")
```

### Server API with Custom Redirect

```bash
# Start auth with custom redirect
curl -X POST http://localhost:1455/auth/codex/start \
  -H "Content-Type: application/json" \
  -d '{"redirect_uri": "http://localhost:8001/api/settings/codex/callback"}'

# Response:
# {
#   "authorize_url": "https://auth.openai.com/...",
#   "redirect_uri": "http://localhost:8001/api/settings/codex/callback",
#   "state": "..."
# }
```

### Testing the Integration

1. Start the server: `claw-codex serve`
2. Open the demo: `http://localhost:1455/demo`
3. Enter your custom redirect URI in the "Custom Redirect URI" field
4. Click "Start OAuth" and complete the flow
5. The library will automatically handle the state encoding/decoding

### Important Notes

- The custom redirect URI is encoded in the state parameter using base64
- The library's callback URL (`http://localhost:1455/auth/callback`) must be registered with OpenAI
- Your custom redirect URI doesn't need to be registered with OpenAI
- This approach enables seamless integration without requiring multiple OAuth app registrations

## CLI Authentication and Chat

- Start server (existing behavior):
  - `claw-codex`
- Interactive CLI auth:
  - `claw-codex auth login --open-browser`
- Check auth state:
  - `claw-codex auth status`
- Exchange pasted redirect URL/code:
  - `claw-codex auth exchange 'http://localhost:1455/auth/callback?code=...&state=...'`
- Send a prompt via library client:
  - `claw-codex chat "Write a short haiku" --text-only`

Credentials are stored in `~/.claw-codex/auth.json` by default.

## UI and Local Proxy

Run:

```bash
claw-codex serve
```

Then open:

- Demo UI: `http://<host-or-ip>:1455/demo`
- Start auth via API: `POST /auth/codex/start`
- Chat endpoint: `POST /v1/chat/completions`

If you bind to all interfaces (`CLAW_CODEX_HOST=0.0.0.0`), open the demo with your machine IP:
`http://<your-machine-ip>:1455/demo`.

## Test Mode (no real OAuth)

```bash
CLAW_CODEX_MOCK=1 pytest
```

## Testing

```bash
pytest
```

## Publishing

Release/publish steps are maintained in `AGENTS.md` (Contributor Guide).
First-time registry setup details are in `docs/PUBLISHING.md`.
Library API details and streaming examples are in `docs/LIBRARY.md`.
