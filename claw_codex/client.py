import asyncio
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from .codex import build_request_body, collect_codex_response, iter_codex_events
from .config import AUTH_FILE, DEFAULT_MODEL, MOCK_MODE, ORIGINATOR, PKCE_FILE, REDIRECT_URI
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

SUPPORTED_MODELS = {"claw/codex", "claw/codex-responses", "openai-codex"}


@dataclass
class AuthStartResult:
    authorize_url: str
    redirect_uri: str
    state: str


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


def convert_messages(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
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


def convert_tools(tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
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


class AsyncClawCodexClient:
    def __init__(
        self,
        *,
        auth_file: Optional[Path] = None,
        pkce_file: Optional[Path] = None,
        model: str = DEFAULT_MODEL,
        originator: str = ORIGINATOR,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self.auth_file = Path(auth_file) if auth_file else AUTH_FILE
        self.pkce_file = Path(pkce_file) if pkce_file else PKCE_FILE
        self.model = model
        self.originator = originator
        self.mock_mode = MOCK_MODE if mock_mode is None else mock_mode

    def auth_status(self) -> Dict[str, Any]:
        creds = load_credentials(path=self.auth_file)
        if not creds:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "expires": creds.expires,
            "account_id": creds.account_id,
            "valid": credentials_valid(creds),
        }

    def start_auth(self, originator: Optional[str] = None) -> AuthStartResult:
        oauth_state, url = build_authorize_url(originator or self.originator)
        save_pkce(oauth_state, path=self.pkce_file)
        return AuthStartResult(authorize_url=url, redirect_uri=REDIRECT_URI, state=oauth_state.state)

    async def exchange_code(self, code_or_url: str) -> OAuthCredentials:
        code, state = parse_authorization_input(code_or_url)
        if not code:
            raise ValueError("Missing authorization code")

        if self.mock_mode:
            creds = _mock_credentials()
            save_credentials(creds, path=self.auth_file)
            return creds

        pkce = load_pkce(state, path=self.pkce_file)
        if not pkce:
            raise RuntimeError(
                "Missing PKCE state. Call start_auth() and use the full redirect URL (including state)."
            )

        creds = await exchange_authorization_code(code, pkce.verifier)
        save_credentials(creds, path=self.auth_file)
        return creds

    async def refresh(self) -> OAuthCredentials:
        creds = load_credentials(path=self.auth_file)
        if not creds:
            raise RuntimeError("No credentials to refresh")
        if self.mock_mode:
            refreshed = _mock_credentials()
        else:
            refreshed = await refresh_access_token(creds.refresh)
        save_credentials(refreshed, path=self.auth_file)
        return refreshed

    async def ensure_credentials(self, *, auto_refresh: bool = True) -> OAuthCredentials:
        creds = load_credentials(path=self.auth_file)
        if not creds:
            raise RuntimeError("No Codex OAuth credentials found")
        if credentials_valid(creds):
            return creds
        if not auto_refresh:
            raise RuntimeError("Codex OAuth credentials expired; refresh required")
        return await self.refresh()

    async def chat_completions(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: str = "claw/codex",
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if model not in SUPPORTED_MODELS:
            raise ValueError("Unsupported model. Use claw/codex")
        if not isinstance(messages, list):
            raise ValueError("messages must be an array")

        converted = convert_messages(messages)
        body = build_request_body(
            model=self.model,
            instructions=converted["instructions"],
            input_messages=converted["input"],
            temperature=temperature,
            tools=convert_tools(tools),
            tool_choice=tool_choice,
            session_id=session_id,
        )

        creds = await self.ensure_credentials(auto_refresh=True)
        completion_id = f"chatcmpl_{uuid.uuid4().hex}"
        created = int(time.time())
        text, usage, finish_reason = await collect_codex_response(
            creds.access,
            creds.account_id,
            body,
            session_id=session_id,
            mock_mode=self.mock_mode,
        )
        return {
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

    async def stream_chat_completions(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: str = "claw/codex",
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if model not in SUPPORTED_MODELS:
            raise ValueError("Unsupported model. Use claw/codex")
        if not isinstance(messages, list):
            raise ValueError("messages must be an array")

        converted = convert_messages(messages)
        body = build_request_body(
            model=self.model,
            instructions=converted["instructions"],
            input_messages=converted["input"],
            temperature=temperature,
            tools=convert_tools(tools),
            tool_choice=tool_choice,
            session_id=session_id,
        )

        creds = await self.ensure_credentials(auto_refresh=True)
        completion_id = f"chatcmpl_{uuid.uuid4().hex}"
        created = int(time.time())
        sent_role = False
        async for event in iter_codex_events(
            creds.access,
            creds.account_id,
            body,
            session_id=session_id,
            mock_mode=self.mock_mode,
        ):
            event_type = event.get("type")
            if event_type == "response.output_text.delta":
                delta = event.get("delta")
                if isinstance(delta, str):
                    if not sent_role:
                        sent_role = True
                        yield {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                        }
                    yield {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
                    }
            elif event_type == "response.completed":
                yield {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
            elif event_type == "error":
                raise RuntimeError(f"Codex error: {event}")
            elif event_type == "response.failed":
                raise RuntimeError("Codex response failed")


class ClawCodexClient:
    def __init__(
        self,
        *,
        auth_file: Optional[Path] = None,
        pkce_file: Optional[Path] = None,
        model: str = DEFAULT_MODEL,
        originator: str = ORIGINATOR,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self._client = AsyncClawCodexClient(
            auth_file=auth_file,
            pkce_file=pkce_file,
            model=model,
            originator=originator,
            mock_mode=mock_mode,
        )

    @property
    def auth_file(self) -> Path:
        return self._client.auth_file

    @property
    def pkce_file(self) -> Path:
        return self._client.pkce_file

    def _run(self, coro: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError("Use AsyncClawCodexClient in async contexts")

    def auth_status(self) -> Dict[str, Any]:
        return self._client.auth_status()

    def start_auth(self, originator: Optional[str] = None) -> AuthStartResult:
        return self._client.start_auth(originator=originator)

    def exchange_code(self, code_or_url: str) -> OAuthCredentials:
        return self._run(self._client.exchange_code(code_or_url))

    def refresh(self) -> OAuthCredentials:
        return self._run(self._client.refresh())

    def chat_completions(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: str = "claw/codex",
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._run(
            self._client.chat_completions(
                messages=messages,
                model=model,
                temperature=temperature,
                tools=tools,
                tool_choice=tool_choice,
                session_id=session_id,
            )
        )
