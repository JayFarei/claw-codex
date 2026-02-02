import os
from pathlib import Path

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"
JWT_CLAIM_PATH = "https://api.openai.com/auth"
CODEX_URL = "https://chatgpt.com/backend-api/codex/responses"

SUCCESS_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Authentication successful</title>
</head>
<body>
  <p>Authentication successful. Return to your terminal to continue.</p>
</body>
</html>"""

def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEFAULT_MODEL = os.getenv("CLAW_CODEX_MODEL", "gpt-5.2")
ORIGINATOR = os.getenv("CLAW_CODEX_ORIGINATOR", "pi")
MOCK_MODE = _is_truthy(os.getenv("CLAW_CODEX_MOCK", ""))

DEFAULT_AUTH_DIR = Path(os.getenv("CLAW_CODEX_AUTH_DIR", Path.home() / ".claw-codex"))
AUTH_FILE = Path(os.getenv("CLAW_CODEX_AUTH_FILE", DEFAULT_AUTH_DIR / "auth.json"))
PKCE_FILE = Path(os.getenv("CLAW_CODEX_PKCE_FILE", DEFAULT_AUTH_DIR / "pkce.json"))
