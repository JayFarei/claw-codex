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

## Library Quickstart (recommended for other projects)

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

- Demo UI: `http://127.0.0.1:1455/demo`
- Start auth via API: `POST /auth/codex/start`
- Chat endpoint: `POST /v1/chat/completions`

## Test Mode (no real OAuth)

```bash
CLAW_CODEX_MOCK=1 pytest
```

## Testing

```bash
pytest
```

## Publishing

The repo is configured for **GitHub Actions trusted publishing** to TestPyPI/PyPI.

Quick release flow:

1. Bump `version` in `pyproject.toml`.
2. Commit, tag, and push:
   ```bash
   git add .
   git commit -m "release: claw-codex vX.Y.Z"
   git tag -a vX.Y.Z -m "claw-codex vX.Y.Z"
   git push origin main --tags
   ```
3. Create a GitHub Release for that tag (Actions `Publish` runs automatically and uploads to PyPI).

Optional preflight checks:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

See `docs/PUBLISHING.md` for first-time setup and TestPyPI workflow details.
Library API details and streaming examples are in `docs/LIBRARY.md`.
