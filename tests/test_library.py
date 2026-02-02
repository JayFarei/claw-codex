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


def test_custom_redirect_uri(tmp_path):
    """Test that custom redirect_uri is properly stored and used."""
    custom_redirect = "http://localhost:8001/api/settings/codex/callback"
    client = ClawCodexClient(
        auth_file=tmp_path / "auth.json",
        pkce_file=tmp_path / "pkce.json",
        mock_mode=True,
    )

    # Start auth with custom redirect_uri
    started = client.start_auth(redirect_uri=custom_redirect)
    assert started.authorize_url
    assert started.state
    assert started.redirect_uri == custom_redirect
    assert (tmp_path / "pkce.json").exists()

    # Verify the PKCE state was stored with the custom redirect_uri
    import json
    pkce_data = json.loads((tmp_path / "pkce.json").read_text())
    # PKCE is stored as a list of entries
    if isinstance(pkce_data, list):
        assert pkce_data[0]["redirect_uri"] == custom_redirect
    else:
        assert pkce_data["redirect_uri"] == custom_redirect

    # Complete the flow
    creds = client.exchange_code("mock")
    assert creds.account_id == "mock-account"


def test_approach_b_state_encoding():
    """Test Approach B: state parameter encoding/decoding for custom redirect."""
    from claw_codex.oauth import _encode_state_with_redirect, _decode_state, build_authorize_url
    
    original_state = "abc123"
    actual_redirect = "http://localhost:8001/api/settings/codex/callback"
    
    # Encode state with redirect
    encoded = _encode_state_with_redirect(original_state, actual_redirect)
    assert encoded != original_state
    
    # Decode and verify
    decoded_state, decoded_redirect = _decode_state(encoded)
    assert decoded_state == original_state
    assert decoded_redirect == actual_redirect
    
    # Test with build_authorize_url
    oauth_state, url = build_authorize_url("test", redirect_uri=actual_redirect)
    
    # The URL should use the library's default redirect
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A1455%2Fauth%2Fcallback" in url
    
    # But the state should be encoded with the actual redirect
    assert oauth_state.redirect_uri == actual_redirect
