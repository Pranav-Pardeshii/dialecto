import asyncio

import structlog
from fastapi import APIRouter, Depends, File, UploadFile
from groq import APIError

from app.ai.llm.client import get_groq_client
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.limits import speech_rate_limiter
from app.schemas.speech import TranscriptionResponse
from app.schemas.user import UserOut

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/speech", tags=["Speech Recognition"])

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE = 64 * 1024  # 64 KB

ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/x-m4a",
    "audio/m4a",
    "video/mp4",
    "video/webm",
}


def _validate_audio_format(content: bytes, filename: str) -> bool:
    """Basic format signature check on audio bytes."""
    if len(content) < 4:
        return False
    # WAV: RIFF header
    if content.startswith(b"RIFF"):
        return True
    # OGG: OggS header
    if content.startswith(b"OggS"):
        return True
    # MP3: ID3 tag or sync word
    if content.startswith(b"ID3") or (content[0] == 0xFF and (content[1] & 0xE0) == 0xE0):
        return True
    # WEBM / MKV: EBML header
    if content.startswith(b"\x1a\x45\xdf\xa3"):
        return True
    # MP4 / M4A: ftyp atom in first 16 bytes
    if b"ftyp" in content[:16]:
        return True
    # If filename ends with recognized audio extension, accept as fallback
    lower_fn = filename.lower()
    if any(lower_fn.endswith(ext) for ext in [".wav", ".mp3", ".m4a", ".ogg", ".webm", ".mp4"]):
        return True
    return False


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: UserOut = Depends(get_current_user),
) -> TranscriptionResponse:
    """Transcribe spoken learner audio using Whisper speech-to-text model."""
    settings = get_settings()

    # Apply rate limiting per user
    speech_rate_limiter.check(current_user.id)

    # Validate declared MIME type if provided
    if audio.content_type and audio.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise AppError(
            code="invalid_audio_format",
            message=f"Unsupported audio format '{audio.content_type}'. Supported formats: webm, mp4, wav, mp3, ogg.",
            status_code=400,
        )

    # Bounded read to avoid memory exhaustion attacks
    total_bytes = 0
    chunks: list[bytes] = []

    try:
        while True:
            chunk = await audio.read(CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_AUDIO_BYTES:
                raise AppError(
                    code="audio_too_large",
                    message=f"Audio file exceeds maximum size limit of {MAX_AUDIO_BYTES // (1024 * 1024)} MB",
                    status_code=400,
                )
            chunks.append(chunk)
    finally:
        await audio.close()

    content = b"".join(chunks)

    if len(content) == 0:
        raise AppError(
            code="audio_empty",
            message="Uploaded audio file contains no data",
            status_code=400,
        )

    filename = audio.filename or "recording.webm"
    if not _validate_audio_format(content, filename):
        raise AppError(
            code="invalid_audio_format",
            message="Uploaded file is not a recognized audio format",
            status_code=400,
        )

    try:
        client = get_groq_client()
        async with asyncio.timeout(20.0):
            transcription = await client.audio.transcriptions.create(
                file=(filename, content),
                model=settings.WHISPER_MODEL,
            )
        return TranscriptionResponse(text=transcription.text)
    except TimeoutError:
        logger.warning("speech_transcription_timeout")
        raise AppError(
            code="transcription_timeout",
            message="Speech transcription request timed out",
            status_code=504,
        )
    except APIError as api_err:
        logger.warning("speech_transcription_api_error", error=str(api_err))
        raise AppError(
            code="transcription_failed",
            message="Speech transcription service encountered an error",
            status_code=502,
        )
    except Exception as exc:
        logger.error("speech_transcription_unexpected_error", error=str(exc))
        raise AppError(
            code="transcription_failed",
            message="Failed to process audio recording",
            status_code=500,
        )
