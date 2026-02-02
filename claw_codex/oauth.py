import base64
import hashlib
import json
import os
import secrets
import time
from typing import Optional, Tuple

import httpx

from .config import AUTHORIZE_URL, CLIENT_ID, JWT_CLAIM_PATH, REDIRECT_URI, SCOPE, TOKEN_URL
from .storage import OAuthCredentials, OAuthState


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_pkce() -> Tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def create_state() -> str:
    return secrets.token_hex(16)


def _encode_state_with_redirect(state: str, actual_redirect_uri: str) -> str:
    """Encode the actual redirect URI into the state parameter using base64."""
    payload = json.dumps({"s": state, "r": actual_redirect_uri})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_state(state: str) -> Tuple[str, Optional[str]]:
    """Decode state parameter to extract original state and actual redirect URI."""
    try:
        padding = "=" * (-len(state) % 4)
        decoded = base64.urlsafe_b64decode(state + padding)
        payload = json.loads(decoded.decode("utf-8"))
        return payload.get("s", state), payload.get("r")
    except Exception:
        return state, None


def build_authorize_url(originator: str, redirect_uri: Optional[str] = None) -> Tuple[OAuthState, str]:
    verifier, challenge = generate_pkce()
    state = create_state()
    
    # Approach B: Always use library's registered redirect in the OAuth URL
    # If a custom redirect is provided, encode it in the state parameter
    if redirect_uri is not None and redirect_uri != REDIRECT_URI:
        oauth_state = OAuthState(
            verifier=verifier,
            state=state,
            created_at=int(time.time() * 1000),
            redirect_uri=redirect_uri,
        )
        state = _encode_state_with_redirect(state, redirect_uri)
    else:
        oauth_state = OAuthState(
            verifier=verifier,
            state=state,
            created_at=int(time.time() * 1000),
            redirect_uri=None,
        )
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": originator,
    }
    url = httpx.URL(AUTHORIZE_URL).copy_merge_params(params)
    return oauth_state, str(url)


def parse_authorization_input(value: str) -> Tuple[Optional[str], Optional[str]]:
    raw = value.strip()
    if not raw:
        return None, None

    if raw.startswith("http://") or raw.startswith("https://"):
        try:
            url = httpx.URL(raw)
            code = url.params.get("code")
            state = url.params.get("state")
            if code:
                return code, state
        except Exception:
            pass

    if "#" in raw:
        code, state = raw.split("#", 1)
        return code or None, state or None

    if "code=" in raw:
        params = httpx.QueryParams(raw)
        code = params.get("code")
        state = params.get("state")
        return code, state

    return raw, None


def _decode_jwt_payload(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return None


def extract_account_id(access_token: str) -> str:
    payload = _decode_jwt_payload(access_token)
    auth = payload.get(JWT_CLAIM_PATH, {}) if isinstance(payload, dict) else {}
    account_id = auth.get("chatgpt_account_id") if isinstance(auth, dict) else None
    if not account_id:
        raise ValueError("Failed to extract accountId from token")
    return str(account_id)


async def exchange_authorization_code(code: str, verifier: str, redirect_uri: str = REDIRECT_URI) -> OAuthCredentials:
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if resp.status_code >= 400:
        raise RuntimeError(f"Token exchange failed: {resp.status_code} {resp.text}")
    payload = resp.json()
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    try:
        expires_in = int(payload.get("expires_in"))
    except Exception:
        expires_in = None
    if not access or not refresh or expires_in is None:
        raise RuntimeError("Token response missing fields")
    expires = int(time.time() * 1000) + (expires_in * 1000)
    account_id = extract_account_id(access)
    return OAuthCredentials(access=access, refresh=refresh, expires=expires, account_id=account_id)


async def refresh_access_token(refresh_token: str) -> OAuthCredentials:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if resp.status_code >= 400:
        raise RuntimeError(f"Token refresh failed: {resp.status_code} {resp.text}")
    payload = resp.json()
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    try:
        expires_in = int(payload.get("expires_in"))
    except Exception:
        expires_in = None
    if not access or not refresh or expires_in is None:
        raise RuntimeError("Token refresh response missing fields")
    expires = int(time.time() * 1000) + (expires_in * 1000)
    account_id = extract_account_id(access)
    return OAuthCredentials(access=access, refresh=refresh, expires=expires, account_id=account_id)
