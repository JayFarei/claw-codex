import json
import platform
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx

from .config import CODEX_URL, MOCK_MODE


def build_headers(access_token: str, account_id: str, session_id: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "OpenAI-Beta": "responses=experimental",
        "originator": "pi",
        "User-Agent": f"pi ({platform.system()} {platform.release()}; {platform.machine()})",
        "accept": "text/event-stream",
        "content-type": "application/json",
    }
    if session_id:
        headers["session_id"] = session_id
    return headers


def build_request_body(
    model: str,
    instructions: Optional[str],
    input_messages: List[Dict[str, Any]],
    temperature: Optional[float],
    tools: Optional[List[Dict[str, Any]]],
    tool_choice: Optional[Any],
    session_id: Optional[str],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "model": model,
        "store": False,
        "stream": True,
        "instructions": instructions,
        "input": input_messages,
        "text": {"verbosity": "medium"},
        "include": ["reasoning.encrypted_content"],
        "prompt_cache_key": session_id,
        "tool_choice": "auto",
        "parallel_tool_calls": True,
    }
    if temperature is not None:
        body["temperature"] = temperature
    if tools:
        body["tools"] = tools
    if tool_choice is not None:
        body["tool_choice"] = tool_choice
    return body


async def iter_codex_events(
    access_token: str,
    account_id: str,
    body: Dict[str, Any],
    session_id: Optional[str] = None,
    mock_mode: Optional[bool] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    use_mock_mode = MOCK_MODE if mock_mode is None else mock_mode
    if use_mock_mode:
        async for event in _mock_codex_events(body):
            yield event
        return

    headers = build_headers(access_token, account_id, session_id)
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", CODEX_URL, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                text = await resp.aread()
                raise RuntimeError(f"Codex request failed: {resp.status_code} {text.decode('utf-8', 'ignore')}")

            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    part, buffer = buffer.split("\n\n", 1)
                    data_lines = [line[5:].strip() for line in part.split("\n") if line.startswith("data:")]
                    if not data_lines:
                        continue
                    data = "\n".join(data_lines).strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        event = json.loads(data)
                    except Exception:
                        continue
                    if isinstance(event, dict):
                        yield event


async def collect_codex_response(
    access_token: str,
    account_id: str,
    body: Dict[str, Any],
    session_id: Optional[str] = None,
    mock_mode: Optional[bool] = None,
) -> Tuple[str, Dict[str, int], Optional[str]]:
    text_parts: List[str] = []
    usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    finish_reason: Optional[str] = None

    async for event in iter_codex_events(
        access_token,
        account_id,
        body,
        session_id=session_id,
        mock_mode=mock_mode,
    ):
        event_type = event.get("type")
        if event_type == "response.output_text.delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                text_parts.append(delta)
        elif event_type == "response.completed":
            response = event.get("response") or {}
            status = response.get("status")
            finish_reason = "stop" if status == "completed" else "stop"
            usage_obj = response.get("usage") or {}
            usage["prompt_tokens"] = int(usage_obj.get("input_tokens", 0))
            usage["completion_tokens"] = int(usage_obj.get("output_tokens", 0))
            usage["total_tokens"] = int(usage_obj.get("total_tokens", 0))
        elif event_type == "error":
            raise RuntimeError(f"Codex error: {event}")
        elif event_type == "response.failed":
            raise RuntimeError("Codex response failed")

    return "".join(text_parts), usage, finish_reason


def format_openrouter_message(content: str) -> Dict[str, Any]:
    return {"role": "assistant", "content": content}


def _extract_last_user_text(body: Dict[str, Any]) -> str:
    messages = body.get("input") or []
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") in {"text", "input_text", "output_text"}:
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return " ".join(parts).strip()
        if isinstance(content, str):
            return content.strip()
    return ""


def _estimate_tokens(text: str) -> int:
    words = [w for w in text.replace("\n", " ").split(" ") if w]
    return max(1, len(words)) if text else 0


async def _mock_codex_events(body: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    user_text = _extract_last_user_text(body)
    if user_text:
        response_text = f"Mock Codex response to: {user_text}"
    else:
        response_text = "Mock Codex response."

    for i in range(0, len(response_text), 16):
        yield {"type": "response.output_text.delta", "delta": response_text[i : i + 16]}

    usage = {
        "input_tokens": _estimate_tokens(user_text),
        "output_tokens": _estimate_tokens(response_text),
        "total_tokens": _estimate_tokens(user_text) + _estimate_tokens(response_text),
    }
    yield {"type": "response.completed", "response": {"status": "completed", "usage": usage}}
