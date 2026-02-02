import asyncio

from claw_codex.client import AsyncClawCodexClient, ClawCodexClient


def test_sync_client_mock_auth_and_chat(tmp_path):
    client = ClawCodexClient(
        auth_file=tmp_path / "auth.json",
        pkce_file=tmp_path / "pkce.json",
        mock_mode=True,
    )

    started = client.start_auth()
    assert started.authorize_url
    assert started.state
    assert (tmp_path / "pkce.json").exists()

    creds = client.exchange_code("mock")
    assert creds.account_id == "mock-account"
    status = client.auth_status()
    assert status["authenticated"] is True

    completion = client.chat_completions(
        model="claw/codex",
        messages=[
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": "Say hello"},
        ],
    )
    assert completion["object"] == "chat.completion"
    assert "Mock Codex response" in completion["choices"][0]["message"]["content"]


def test_async_client_mock_stream(tmp_path):
    async def _collect_chunks():
        client = AsyncClawCodexClient(
            auth_file=tmp_path / "auth.json",
            pkce_file=tmp_path / "pkce.json",
            mock_mode=True,
        )
        await client.exchange_code("mock")
        chunks = []
        async for chunk in client.stream_chat_completions(
            model="claw/codex",
            messages=[{"role": "user", "content": "Stream hello"}],
        ):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(_collect_chunks())
    assert len(chunks) >= 2
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
