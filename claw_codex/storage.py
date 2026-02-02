import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import AUTH_FILE, PKCE_FILE


@dataclass
class OAuthCredentials:
    access: str
    refresh: str
    expires: int
    account_id: str


@dataclass
class OAuthState:
    verifier: str
    state: str
    created_at: int
    redirect_uri: Optional[str] = None


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_credentials(creds: OAuthCredentials, path: Path = AUTH_FILE) -> None:
    _ensure_parent(path)
    data = {
        "access": creds.access,
        "refresh": creds.refresh,
        "expires": creds.expires,
        "account_id": creds.account_id,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_credentials(path: Path = AUTH_FILE) -> Optional[OAuthCredentials]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return OAuthCredentials(
            access=str(data.get("access", "")),
            refresh=str(data.get("refresh", "")),
            expires=int(data.get("expires", 0)),
            account_id=str(data.get("account_id", "")),
        )
    except Exception:
        return None


def credentials_valid(creds: OAuthCredentials, min_ttl_seconds: int = 60) -> bool:
    return creds.expires > int(time.time() * 1000) + (min_ttl_seconds * 1000)


def save_pkce(state: OAuthState, path: Path = PKCE_FILE, max_entries: int = 5) -> None:
    _ensure_parent(path)
    entries: list[dict] = []
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                entries = [e for e in raw if isinstance(e, dict)]
            elif isinstance(raw, dict):
                entries = [raw]
        except Exception:
            entries = []

    entries = [e for e in entries if e.get("state") != state.state]
    entry = {"verifier": state.verifier, "state": state.state, "created_at": state.created_at}
    if state.redirect_uri is not None:
        entry["redirect_uri"] = state.redirect_uri
    entries.insert(0, entry)
    entries = entries[: max_entries if max_entries > 0 else 1]
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def load_pkce(state: Optional[str] = None, path: Path = PKCE_FILE) -> Optional[OAuthState]:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    entries: list[dict] = []
    if isinstance(raw, list):
        entries = [e for e in raw if isinstance(e, dict)]
    elif isinstance(raw, dict):
        entries = [raw]

    if not entries:
        return None

    if state:
        for entry in entries:
            if entry.get("state") == state:
                return OAuthState(
                    verifier=str(entry.get("verifier", "")),
                    state=str(entry.get("state", "")),
                    created_at=int(entry.get("created_at", 0)),
                    redirect_uri=entry.get("redirect_uri"),
                )
        return None

    if len(entries) == 1:
        entry = entries[0]
        return OAuthState(
            verifier=str(entry.get("verifier", "")),
            state=str(entry.get("state", "")),
            created_at=int(entry.get("created_at", 0)),
            redirect_uri=entry.get("redirect_uri"),
        )

    return None
