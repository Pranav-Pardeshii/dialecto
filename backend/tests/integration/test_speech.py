import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transcribe_audio_unauthenticated_rejected(client: AsyncClient) -> None:
    file_content = b"RIFF....WAVEfmt ...."
    files = {"audio": ("test.wav", io.BytesIO(file_content), "audio/wav")}
    res = await client.post("/api/v1/speech/transcriptions", files=files)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_transcribe_audio_success(client: AsyncClient) -> None:
    fake_whisper_resp = MagicMock()
    fake_whisper_resp.text = "Water is split by light into hydrogen and oxygen."

    with patch("app.api.v1.endpoints.speech.get_groq_client") as mock_get_client:
        mock_groq = AsyncMock()
        mock_groq.audio.transcriptions.create.return_value = fake_whisper_resp
        mock_get_client.return_value = mock_groq

        file_content = b"RIFF....WAVEfmt ...."
        files = {"audio": ("test.wav", io.BytesIO(file_content), "audio/wav")}

        res = await client.post(
            "/api/v1/speech/transcriptions",
            files=files,
            headers={"X-Demo-User-Id": "1"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["text"] == "Water is split by light into hydrogen and oxygen."


@pytest.mark.asyncio
async def test_transcribe_audio_empty_file_rejected(client: AsyncClient) -> None:
    files = {"audio": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    res = await client.post(
        "/api/v1/speech/transcriptions",
        files=files,
        headers={"X-Demo-User-Id": "1"},
    )
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "audio_empty"
