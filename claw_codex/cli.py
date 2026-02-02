import argparse
import json
import os
import sys
import webbrowser
from typing import Any

import uvicorn

from .client import ClawCodexClient


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2))


def _run_server(host: str, port: int) -> None:
    uvicorn.run("claw_codex.app:app", host=host, port=port, log_level="info")


def _auth_start(client: ClawCodexClient, args: argparse.Namespace) -> None:
    result = client.start_auth(originator=args.originator)
    payload = {
        "authorize_url": result.authorize_url,
        "redirect_uri": result.redirect_uri,
        "state": result.state,
    }
    _print_json(payload)
    if args.open_browser:
        webbrowser.open(result.authorize_url)


def _auth_exchange(client: ClawCodexClient, args: argparse.Namespace) -> None:
    code_input = args.code or input("Paste redirect URL or code: ").strip()
    creds = client.exchange_code(code_input)
    _print_json({"ok": True, "expires": creds.expires, "account_id": creds.account_id})


def _auth_login(client: ClawCodexClient, args: argparse.Namespace) -> None:
    result = client.start_auth(originator=args.originator)
    print("Open this URL to authorize:")
    print(result.authorize_url)
    if args.open_browser:
        webbrowser.open(result.authorize_url)
    code_input = input("Paste redirect URL or code: ").strip()
    creds = client.exchange_code(code_input)
    _print_json({"ok": True, "expires": creds.expires, "account_id": creds.account_id})


def _auth_status(client: ClawCodexClient) -> None:
    _print_json(client.auth_status())


def _auth_refresh(client: ClawCodexClient) -> None:
    creds = client.refresh()
    _print_json({"ok": True, "expires": creds.expires, "account_id": creds.account_id})


def _chat(client: ClawCodexClient, args: argparse.Namespace) -> None:
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.prompt})
    response = client.chat_completions(messages=messages, model=args.model)
    if args.text_only:
        text = response["choices"][0]["message"]["content"]
        print(text)
        return
    _print_json(response)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Claw Codex OAuth proxy and library CLI")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the local FastAPI proxy server")
    serve_parser.add_argument("--host", default=os.getenv("CLAW_CODEX_HOST", "127.0.0.1"))
    serve_parser.add_argument("--port", type=int, default=int(os.getenv("CLAW_CODEX_PORT", "1455")))

    auth_parser = subparsers.add_parser("auth", help="Authenticate with Codex OAuth")
    auth_sub = auth_parser.add_subparsers(dest="auth_command", required=True)

    auth_start = auth_sub.add_parser("start", help="Generate OAuth URL and persist PKCE state")
    auth_start.add_argument("--originator", default=os.getenv("CLAW_CODEX_ORIGINATOR", "pi"))
    auth_start.add_argument("--open-browser", action="store_true")

    auth_exchange = auth_sub.add_parser("exchange", help="Exchange redirect URL/code for credentials")
    auth_exchange.add_argument("code", nargs="?", default=None)

    auth_login = auth_sub.add_parser("login", help="Interactive login flow")
    auth_login.add_argument("--originator", default=os.getenv("CLAW_CODEX_ORIGINATOR", "pi"))
    auth_login.add_argument("--open-browser", action="store_true")

    auth_sub.add_parser("status", help="Show current auth status")
    auth_sub.add_parser("refresh", help="Refresh access token")

    chat_parser = subparsers.add_parser("chat", help="Send one prompt with OpenRouter-style messages")
    chat_parser.add_argument("prompt", help="User prompt text")
    chat_parser.add_argument("--system", default=None, help="Optional system instruction")
    chat_parser.add_argument("--model", default="claw/codex")
    chat_parser.add_argument("--text-only", action="store_true", help="Print assistant text only")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        host = os.getenv("CLAW_CODEX_HOST", "127.0.0.1")
        port = int(os.getenv("CLAW_CODEX_PORT", "1455"))
        _run_server(host, port)
        return

    if args.command == "serve":
        _run_server(args.host, args.port)
        return

    client = ClawCodexClient(mock_mode=os.getenv("CLAW_CODEX_MOCK", "").strip().lower() in {"1", "true", "yes", "on"})

    try:
        if args.command == "auth":
            if args.auth_command == "start":
                _auth_start(client, args)
            elif args.auth_command == "exchange":
                _auth_exchange(client, args)
            elif args.auth_command == "login":
                _auth_login(client, args)
            elif args.auth_command == "status":
                _auth_status(client)
            elif args.auth_command == "refresh":
                _auth_refresh(client)
            return

        if args.command == "chat":
            _chat(client, args)
            return
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

    parser.print_help()


if __name__ == "__main__":
    main()
