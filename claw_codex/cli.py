import os

import uvicorn


def main() -> None:
    host = os.getenv("CLAW_CODEX_HOST", "127.0.0.1")
    port = int(os.getenv("CLAW_CODEX_PORT", "1455"))
    uvicorn.run("claw_codex.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
