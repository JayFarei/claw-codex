import importlib

from fastapi.testclient import TestClient


def _build_client(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAW_CODEX_MOCK", "1")
    monkeypatch.setenv("CLAW_CODEX_AUTH_DIR", str(tmp_path))
    monkeypatch.setenv("CLAW_CODEX_AUTH_FILE", str(tmp_path / "auth.json"))
    monkeypatch.setenv("CLAW_CODEX_PKCE_FILE", str(tmp_path / "pkce.json"))

    config = importlib.import_module("claw_codex.config")
    storage = importlib.import_module("claw_codex.storage")
    oauth = importlib.import_module("claw_codex.oauth")
    codex = importlib.import_module("claw_codex.codex")
    app_module = importlib.import_module("claw_codex.app")

    importlib.reload(config)
    importlib.reload(storage)
    importlib.reload(oauth)
    importlib.reload(codex)
    importlib.reload(app_module)

    return TestClient(app_module.app)


def test_mock_oauth_and_chat(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    start = client.post("/auth/codex/start")
    assert start.status_code == 200
    start_payload = start.json()
    assert "authorize_url" in start_payload

    exchange = client.post("/auth/codex/exchange", json={"code": "mock"})
    assert exchange.status_code == 200

    status = client.get("/auth/codex/status")
    assert status.status_code == 200
    assert status.json().get("authenticated") is True

    models = client.get("/v1/models")
    assert models.status_code == 200
    assert any(model.get("id") == "claw/codex" for model in models.json().get("data", []))

    completion = client.post(
        "/v1/chat/completions",
        json={
            "model": "claw/codex",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Say hello"},
            ],
            "stream": False,
        },
    )
    assert completion.status_code == 200
    content = completion.json()["choices"][0]["message"]["content"]
    assert "Mock Codex response" in content
