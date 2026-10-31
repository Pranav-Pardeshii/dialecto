import structlog
from fastapi import APIRouter, File, UploadFile
from groq import APIError

from app.ai.llm.client import get_groq_client
from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.speech import TranscriptionResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/speech", tags=["Speech Recognition"])

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
) -> TranscriptionResponse:
    """Transcribe spoken learner audio using Whisper speech-to-text model."""
    settings = get_settings()
    content = await audio.read()

    if len(content) > MAX_AUDIO_BYTES:
        raise AppError(
            code="audio_too_large",
            message=f"Audio file exceeds maximum size limit of {MAX_AUDIO_BYTES // (1024 * 1024)} MB",
            status_code=400,
        )

    if len(content) == 0:
        raise AppError(
            code="audio_empty",
            message="Uploaded audio file contains no data",
            status_code=400,
        )

    try:
        client = get_groq_client()
        filename = audio.filename or "recording.webm"
        transcription = await client.audio.transcriptions.create(
            file=(filename, content),
            model=settings.WHISPER_MODEL,
        )
        return TranscriptionResponse(text=transcription.text)
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
