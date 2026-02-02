import json
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .codex import build_request_body, collect_codex_response, iter_codex_events
from .config import DEFAULT_MODEL, MOCK_MODE, ORIGINATOR, REDIRECT_URI, SUCCESS_HTML
from .oauth import (
    build_authorize_url,
    exchange_authorization_code,
    parse_authorization_input,
    refresh_access_token,
)
from .storage import (
    OAuthCredentials,
    credentials_valid,
    load_credentials,
    load_pkce,
    save_credentials,
    save_pkce,
)

app = FastAPI(title="Claw Codex OpenRouter Mock", version="0.1.0")

DEMO_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Claw Codex Demo</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #edf3f8;
      --bg-2: #e3edf4;
      --ink: #172033;
      --ink-soft: #53617a;
      --card: #ffffffd9;
      --border: #ccd8e6;
      --accent: #0f766e;
      --accent-2: #14532d;
      --accent-soft: #e4f3f1;
      --danger-soft: #fff2f2;
      --shadow: 0 14px 40px rgba(14, 25, 42, 0.11);
      --radius: 16px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 700px at 90% -10%, #c9e7f7 0%, transparent 60%),
        radial-gradient(1000px 650px at -20% 100%, #d4ebdd 0%, transparent 58%),
        linear-gradient(170deg, var(--bg), var(--bg-2));
      min-height: 100vh;
    }

    header {
      position: relative;
      overflow: hidden;
      background: linear-gradient(128deg, #0b1735, #0d2740 55%, #124858);
      color: #f8fbff;
      padding: 34px 22px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    header::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(420px 140px at 12% -8%, rgba(255, 255, 255, 0.14), transparent 68%),
        radial-gradient(340px 170px at 88% 6%, rgba(140, 217, 198, 0.26), transparent 72%);
      pointer-events: none;
    }

    .hero {
      max-width: 1080px;
      margin: 0 auto;
      position: relative;
      z-index: 1;
    }

    .eyebrow {
      margin: 0;
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      opacity: 0.82;
      font-weight: 700;
    }

    h1 {
      margin: 6px 0 4px;
      font-size: clamp(28px, 3.6vw, 38px);
      font-family: "Fraunces", "Iowan Old Style", "Times New Roman", serif;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .lead {
      margin: 0;
      color: rgba(241, 248, 255, 0.92);
      max-width: 780px;
      font-size: 15px;
    }

    main {
      max-width: 1080px;
      margin: 0 auto;
      padding: 26px 16px 34px;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 16px;
    }

    .card {
      background: var(--card);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: var(--shadow);
    }

    h2 {
      margin: 0 0 10px;
      font-size: 28px;
      letter-spacing: -0.02em;
      font-family: "Fraunces", "Iowan Old Style", "Times New Roman", serif;
    }

    .status {
      margin: 0 0 12px;
      font-size: 14px;
      color: var(--ink-soft);
      font-weight: 600;
    }

    .row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    .row.input-row {
      align-items: stretch;
    }

    .row.input-row input {
      min-width: 0;
      flex: 1 1 260px;
    }

    button {
      border: 1px solid transparent;
      border-radius: 11px;
      padding: 10px 14px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.01em;
      background: linear-gradient(180deg, #105850, #0f766e);
      color: #f7fdfc;
      cursor: pointer;
      transition: transform 120ms ease, filter 120ms ease, box-shadow 140ms ease;
      box-shadow: 0 8px 16px rgba(15, 118, 110, 0.22);
    }

    button:hover {
      transform: translateY(-1px);
      filter: brightness(1.03);
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.6;
      transform: none;
      box-shadow: none;
    }

    button.secondary {
      background: #eef4fa;
      color: #1e2d45;
      border-color: #cfdbeb;
      box-shadow: none;
    }

    label {
      display: block;
      margin: 11px 0 6px;
      font-size: 13px;
      font-weight: 700;
      color: #354562;
    }

    input,
    textarea {
      width: 100%;
      padding: 11px 12px;
      border-radius: 11px;
      border: 1px solid #c7d6e8;
      background: #f9fbfd;
      color: var(--ink);
      font: inherit;
      transition: border-color 120ms ease, box-shadow 120ms ease;
    }

    input:focus,
    textarea:focus {
      outline: none;
      border-color: #4e8fb8;
      box-shadow: 0 0 0 3px rgba(78, 143, 184, 0.16);
      background: #ffffff;
    }

    .url-box {
      border: 1px solid #d2ddeb;
      border-radius: 11px;
      background: #f8fbff;
      padding: 9px 11px;
      max-height: 92px;
      overflow: auto;
    }

    .auth-url {
      display: block;
      color: #1f4f8f;
      text-decoration: none;
      line-height: 1.3;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .auth-url:hover {
      text-decoration: underline;
    }

    .hint {
      margin: 8px 0 0;
      font-size: 12px;
      color: #5d6c86;
    }

    .chat-log {
      min-height: 290px;
      max-height: 420px;
      overflow-y: auto;
      border: 1px solid #d7e1ee;
      border-radius: 12px;
      padding: 10px;
      background: linear-gradient(180deg, #fbfdff, #f4f8fc);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .msg {
      max-width: 100%;
      border-radius: 12px;
      padding: 9px 11px;
      border: 1px solid #d7e3f0;
      background: #ffffff;
    }

    .msg.user {
      align-self: flex-end;
      background: var(--accent-soft);
      border-color: #bce0d7;
    }

    .msg.assistant {
      align-self: flex-start;
    }

    .msg.error {
      background: var(--danger-soft);
      border-color: #f3c4c4;
    }

    .msg strong {
      display: block;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 4px;
      color: #63758f;
    }

    .msg-text {
      margin: 0;
      font-family: inherit;
      line-height: 1.36;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    code {
      font-family: "IBM Plex Mono", "SFMono-Regular", Menlo, Consolas, monospace;
      background: #eaf1f8;
      color: #244066;
      border-radius: 7px;
      padding: 2px 6px;
      font-size: 12px;
    }

    @media (min-width: 900px) {
      .layout {
        grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
      }

      .chat-card {
        min-height: 560px;
      }
    }

    @media (max-width: 700px) {
      header {
        padding: 24px 14px;
      }

      main {
        padding: 16px 10px 26px;
      }

      .card {
        padding: 14px;
      }

      .row {
        flex-direction: column;
        align-items: stretch;
      }

      button {
        width: 100%;
      }

      .chat-log {
        min-height: 240px;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <p class="eyebrow">Local Codex Proxy</p>
      <h1>Claw Codex Demo</h1>
      <p class="lead">Authenticate with Codex OAuth and chat via an OpenRouter-style endpoint.</p>
    </div>
  </header>
  <main>
    <div class="layout">
      <section class="card auth-card">
        <h2>Auth</h2>
        <p class="status" id="auth-status">Status: unknown</p>
        <div class="row">
          <button id="start-auth">Start OAuth</button>
          <button id="check-auth" class="secondary">Check Status</button>
        </div>
        <label>Authorize URL</label>
        <div class="url-box">
          <a class="auth-url" id="auth-url" href="#" target="_blank" rel="noreferrer">not started</a>
        </div>
        <label for="auth-code">Paste redirect URL or code (if callback failed)</label>
        <div class="row input-row">
          <input id="auth-code" placeholder="http://localhost:1455/auth/callback?code=...&state=..." />
          <button id="exchange-auth">Exchange</button>
        </div>
        <p class="hint">Tip: paste the full URL including both <code>code</code> and <code>state</code>.</p>
      </section>

      <section class="card chat-card">
        <h2>Chat</h2>
        <div class="chat-log" id="chat-log"></div>
        <label for="chat-input">Message</label>
        <textarea id="chat-input" rows="3" placeholder="Ask something..."></textarea>
        <div class="row">
          <button id="send-chat">Send</button>
          <button id="clear-chat" class="secondary">Clear</button>
        </div>
        <p class="hint">Model: <code>claw/codex</code></p>
      </section>
    </div>
  </main>
  <script>
    const authStatus = document.getElementById('auth-status');
    const authUrl = document.getElementById('auth-url');
    const authCodeInput = document.getElementById('auth-code');
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat');

    const messages = [
      { role: 'system', content: 'You are a helpful assistant.' }
    ];

    function appendMessage(role, content) {
      const wrap = document.createElement('div');
      const roleLabel = String(role || '').toLowerCase();
      const msgType = roleLabel === 'user' ? 'user' : (roleLabel === 'error' ? 'error' : 'assistant');
      wrap.className = 'msg ' + msgType;

      const title = document.createElement('strong');
      title.textContent = roleLabel || 'assistant';
      wrap.appendChild(title);

      const text = document.createElement('pre');
      text.className = 'msg-text';
      text.textContent = String(content ?? '');
      wrap.appendChild(text);

      chatLog.appendChild(wrap);
      chatLog.scrollTop = chatLog.scrollHeight;
    }

    async function checkStatus() {
      const res = await fetch('/auth/codex/status');
      const data = await res.json();
      authStatus.textContent = data.authenticated ? 'Status: authenticated' : 'Status: not authenticated';
    }

    document.getElementById('start-auth').addEventListener('click', async () => {
      const res = await fetch('/auth/codex/start', { method: 'POST' });
      const data = await res.json();
      authUrl.textContent = data.authorize_url;
      authUrl.href = data.authorize_url;
      window.open(data.authorize_url, '_blank', 'noopener');
    });

    document.getElementById('check-auth').addEventListener('click', checkStatus);

    document.getElementById('exchange-auth').addEventListener('click', async () => {
      const code = authCodeInput.value.trim();
      if (!code) return;
      const res = await fetch('/auth/codex/exchange', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code })
      });
      if (res.ok) {
        authCodeInput.value = '';
        await checkStatus();
      } else {
        let msg = 'Exchange failed';
        try {
          const data = await res.json();
          if (data.detail) msg = data.detail;
        } catch {}
        authStatus.textContent = 'Status: ' + msg;
      }
    });

    document.getElementById('send-chat').addEventListener('click', async () => {
      const content = chatInput.value.trim();
      if (!content) return;
      chatInput.value = '';
      messages.push({ role: 'user', content });
      appendMessage('user', content);
      sendButton.disabled = true;
      try {
        const res = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ model: 'claw/codex', messages, stream: false })
        });
        let data = {};
        try {
          data = await res.json();
        } catch {}
        if (!res.ok) {
          const detail = data?.detail ? String(data.detail) : `HTTP ${res.status}`;
          appendMessage('error', detail);
          return;
        }
        const reply = data?.choices?.[0]?.message?.content || '(no reply)';
        messages.push({ role: 'assistant', content: reply });
        appendMessage('assistant', reply);
      } finally {
        sendButton.disabled = false;
      }
    });

    document.getElementById('clear-chat').addEventListener('click', () => {
      messages.splice(1);
      chatLog.innerHTML = '';
    });

    checkStatus();
  </script>
</body>
</html>
"""


def _ensure_credentials() -> OAuthCredentials:
    creds = load_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="No Codex OAuth credentials found")
    if not credentials_valid(creds):
        raise HTTPException(status_code=401, detail="Codex OAuth credentials expired; refresh required")
    return creds


def _mock_credentials() -> OAuthCredentials:
    return OAuthCredentials(
        access="mock-access-token",
        refresh="mock-refresh-token",
        expires=int(time.time() * 1000) + 3600 * 1000,
        account_id="mock-account",
    )


def _coerce_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _content_to_parts(content: Any, role: str) -> List[Dict[str, Any]]:
    text_type = "output_text" if role == "assistant" else "input_text"

    if isinstance(content, list):
        parts: List[Dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", "")).strip()
            if item_type in {"text", "input_text", "output_text"}:
                if role == "assistant":
                    parts.append(
                        {
                            "type": "output_text",
                            "text": _coerce_text(item.get("text")),
                            "annotations": item.get("annotations") or [],
                        }
                    )
                else:
                    parts.append({"type": "input_text", "text": _coerce_text(item.get("text"))})
            elif role == "assistant" and item_type == "refusal":
                parts.append({"type": "refusal", "refusal": _coerce_text(item.get("refusal"))})
        if parts:
            return parts

    if role == "assistant":
        return [{"type": "output_text", "text": _coerce_text(content), "annotations": []}]
    return [{"type": text_type, "text": _coerce_text(content)}]


def _convert_messages(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    system_parts: List[str] = []
    input_messages: List[Dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            system_parts.append(_coerce_text(content))
            continue
        if not role:
            continue
        normalized_role = str(role)
        if normalized_role == "assistant":
            input_messages.append(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": _content_to_parts(content, normalized_role),
                    "status": "completed",
                    "id": f"msg_{len(input_messages)}",
                }
            )
        else:
            input_messages.append({"role": normalized_role, "content": _content_to_parts(content, normalized_role)})

    instructions = "\n".join([part for part in system_parts if part]) if system_parts else None
    return {"instructions": instructions, "input": input_messages}


def _convert_tools(tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    if not tools:
        return None
    converted: List[Dict[str, Any]] = []
    for tool in tools:
        if tool.get("type") != "function":
            continue
        fn = tool.get("function") or {}
        converted.append(
            {
                "type": "function",
                "name": fn.get("name"),
                "description": fn.get("description"),
                "parameters": fn.get("parameters"),
            }
        )
    return converted or None


@app.get("/auth/codex/status")
async def auth_status() -> JSONResponse:
    creds = load_credentials()
    if not creds:
        return JSONResponse({"authenticated": False})
    return JSONResponse(
        {
            "authenticated": True,
            "expires": creds.expires,
            "account_id": creds.account_id,
        }
    )


@app.post("/auth/codex/start")
async def auth_start(originator: Optional[str] = None) -> JSONResponse:
    oauth_state, url = build_authorize_url(originator or ORIGINATOR)
    save_pkce(oauth_state)
    return JSONResponse({"authorize_url": url, "redirect_uri": REDIRECT_URI, "state": oauth_state.state})


async def _handle_auth_callback(code: Optional[str], state: Optional[str]) -> HTMLResponse:
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    pkce = load_pkce(state)
    if not pkce:
        raise HTTPException(
            status_code=400,
            detail="Missing PKCE state. Call /auth/codex/start and paste the full redirect URL (including state).",
        )
    try:
        creds = await exchange_authorization_code(code, pkce.verifier)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    save_credentials(creds)
    return HTMLResponse(SUCCESS_HTML)


@app.get("/auth/callback")
async def auth_callback_root(code: Optional[str] = None, state: Optional[str] = None) -> HTMLResponse:
    return await _handle_auth_callback(code, state)


@app.get("/auth/codex/callback")
async def auth_callback(code: Optional[str] = None, state: Optional[str] = None) -> HTMLResponse:
    return await _handle_auth_callback(code, state)


@app.post("/auth/codex/exchange")
async def auth_exchange(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    raw = str(payload.get("code", ""))
    code, state = parse_authorization_input(raw)
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if MOCK_MODE:
        creds = _mock_credentials()
        save_credentials(creds)
        return JSONResponse({"ok": True, "expires": creds.expires, "account_id": creds.account_id})
    pkce = load_pkce(state)
    if not pkce:
        raise HTTPException(
            status_code=400,
            detail="Missing PKCE state. Call /auth/codex/start and paste the full redirect URL (including state).",
        )
    try:
        creds = await exchange_authorization_code(code, pkce.verifier)
    except RuntimeError as exc:
        existing = load_credentials()
        if existing and credentials_valid(existing):
            return JSONResponse(
                {
                    "ok": True,
                    "already_authenticated": True,
                    "expires": existing.expires,
                    "account_id": existing.account_id,
                }
            )
        raise HTTPException(status_code=400, detail=str(exc))
    save_credentials(creds)
    return JSONResponse({"ok": True, "expires": creds.expires, "account_id": creds.account_id})


@app.post("/auth/codex/refresh")
async def auth_refresh() -> JSONResponse:
    creds = load_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="No credentials to refresh")
    if MOCK_MODE:
        new_creds = _mock_credentials()
        save_credentials(new_creds)
        return JSONResponse({"ok": True, "expires": new_creds.expires})
    new_creds = await refresh_access_token(creds.refresh)
    save_credentials(new_creds)
    return JSONResponse({"ok": True, "expires": new_creds.expires})


@app.get("/demo")
async def demo() -> HTMLResponse:
    return HTMLResponse(DEMO_HTML)


@app.get("/v1/models")
async def list_models() -> JSONResponse:
    now = int(time.time())
    data = [
        {
            "id": "claw/codex",
            "object": "model",
            "created": now,
            "owned_by": "claw",
        }
    ]
    return JSONResponse({"object": "list", "data": data})


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    payload = await request.json()
    model = payload.get("model")
    if model not in {"claw/codex", "claw/codex-responses", "openai-codex"}:
        raise HTTPException(status_code=400, detail="Unsupported model. Use claw/codex")

    messages = payload.get("messages") or []
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be an array")

    stream = bool(payload.get("stream"))
    temperature = payload.get("temperature")
    tools = _convert_tools(payload.get("tools"))
    tool_choice = payload.get("tool_choice")
    session_id = payload.get("session_id")

    converted = _convert_messages(messages)
    body = build_request_body(
        model=DEFAULT_MODEL,
        instructions=converted["instructions"],
        input_messages=converted["input"],
        temperature=temperature,
        tools=tools,
        tool_choice=tool_choice,
        session_id=session_id,
    )

    creds = load_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="No Codex OAuth credentials found")
    if not credentials_valid(creds):
        creds = await refresh_access_token(creds.refresh)
        save_credentials(creds)

    completion_id = f"chatcmpl_{uuid.uuid4().hex}"
    created = int(time.time())

    if stream:
        async def event_stream() -> Any:
            sent_role = False
            try:
                async for event in iter_codex_events(creds.access, creds.account_id, body, session_id=session_id):
                    event_type = event.get("type")
                    if event_type == "response.output_text.delta":
                        delta = event.get("delta")
                        if isinstance(delta, str):
                            if not sent_role:
                                chunk = {
                                    "id": completion_id,
                                    "object": "chat.completion.chunk",
                                    "created": created,
                                    "model": model,
                                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                                }
                                yield f"data: {json.dumps(chunk)}\n\n"
                                sent_role = True
                            chunk = {
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                    elif event_type == "response.completed":
                        chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                    elif event_type == "error":
                        raise RuntimeError("Codex error event")
                    elif event_type == "response.failed":
                        raise RuntimeError("Codex response failed")
            finally:
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    try:
        text, usage, finish_reason = await collect_codex_response(
            creds.access, creds.account_id, body, session_id=session_id
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    response = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason or "stop",
            }
        ],
        "usage": usage,
    }
    return JSONResponse(response)
