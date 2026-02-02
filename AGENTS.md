# Repository Guidelines

## Project Structure & Module Organization
- Core package: `claw_codex/`.
  - `app.py`: FastAPI app and HTTP routes (`/auth/*`, `/v1/*`, `/demo`).
  - `oauth.py`: OAuth + PKCE helpers and token exchange/refresh logic.
  - `codex.py`: Codex request shaping, SSE parsing, and mock response flow.
  - `storage.py`: credential/PKCE persistence dataclasses and file IO.
  - `config.py`: environment-driven settings and constants.
  - `cli.py` / `__main__.py`: local entry points.
- Tests: `tests/test_e2e.py` (end-to-end API behavior using mock mode).
- Metadata: `pyproject.toml` (deps, script entry point), `README.md` (usage).

## Build, Test, and Development Commands
- Create env and install runtime deps:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -e .`
- Install dev extras (pytest):
  - `pip install -e '.[dev]'`
- Run server locally:
  - `claw-codex`
  - Default bind is `127.0.0.1:1455`.
- Run tests:
  - `pytest`
  - Targeted run: `pytest tests/test_e2e.py -k mock`

## Coding Style & Naming Conventions
- Follow Python 3 style: 4-space indentation, PEP 8 line discipline, explicit imports.
- Keep module/function names `snake_case`; classes/dataclasses `PascalCase`.
- Preserve existing typing style (`Optional[...]`, `Dict[...]`, `List[...]`) in touched files.
- Prefer small, focused helpers for protocol/format parsing and error handling.

## Testing Guidelines
- Framework: `pytest` with `fastapi.testclient.TestClient`.
- Use environment-driven mock mode for deterministic tests:
  - `CLAW_CODEX_MOCK=1` and temp auth file paths.
- Add tests for new endpoints, auth edge cases, and stream/non-stream behavior.
- Name tests `test_<behavior>()` and keep assertions user-visible (status, payload, fields).

## Commit & Pull Request Guidelines
- This workspace snapshot has no local `.git` history, so no project-specific convention can be inferred.
- Recommended commit format: Conventional Commits (e.g., `feat(auth): validate state on exchange`).
- PRs should include:
  - change summary and rationale,
  - test evidence (`pytest` output),
  - config/env changes,
  - sample request/response when API behavior changes.

## Security & Configuration Tips
- Never commit real tokens or `~/.claw-codex/auth.json` contents.
- Prefer env vars for local overrides (`CLAW_CODEX_AUTH_FILE`, `CLAW_CODEX_MODEL`, `CLAW_CODEX_PORT`).
- Treat OAuth callback and token-handling code as high-sensitivity paths; review carefully.
