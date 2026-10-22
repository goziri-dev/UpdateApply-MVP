"""Interview audio → transcript via OpenRouter speech-to-text (Whisper)."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

OPENROUTER_TRANSCRIPTIONS_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
DEFAULT_TRANSCRIBE_MODEL = "openai/whisper-1"
MAX_AUDIO_BYTES = 10 * 1024 * 1024
_TRANSCRIBE_TIMEOUT_S = 60.0

_EXT_TO_FORMAT: dict[str, str] = {
    "webm": "webm",
    "wav": "wav",
    "mp3": "mp3",
    "mpeg": "mp3",
    "mp4": "m4a",
    "m4a": "m4a",
    "ogg": "ogg",
    "oga": "ogg",
    "flac": "flac",
    "aac": "aac",
}

_MIME_TO_FORMAT: dict[str, str] = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/aac": "aac",
}


class TranscribeError(Exception):
    """Raised when interview audio transcription fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "transcription_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InterviewTranscribeService:
    """Bytes + MIME → OpenRouter Whisper transcript (not stored)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def configured(self) -> bool:
        return self.settings.openrouter_configured

    def model(self) -> str:
        override = (self.settings.openrouter_model_interview_transcribe or "").strip()
        return override or DEFAULT_TRANSCRIBE_MODEL

    async def transcribe(
        self,
        data: bytes,
        *,
        filename: str = "recording.webm",
        content_type: str = "audio/webm",
        language: str = "en",
    ) -> str:
        if not data:
            raise TranscribeError(
                "No audio was captured. Tap the mic to record, or type your answer.",
                code="empty_audio",
            )
        if len(data) > MAX_AUDIO_BYTES:
            raise TranscribeError(
                "That recording is too long. Keep answers to a couple of minutes, "
                "or type your answer instead.",
                code="audio_too_large",
            )
        if not self.configured():
            raise TranscribeError(
                "Voice transcription is not configured. Set OPENROUTER_API_KEY "
                "on the server, or type your answer.",
                code="openrouter_unconfigured",
            )

        audio_format = _resolve_format(filename=filename, content_type=content_type)
        model = self.model()
        payload: dict[str, Any] = {
            "model": model,
            "language": language,
            "input_audio": {
                "data": base64.b64encode(data).decode("ascii"),
                "format": audio_format,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key.strip()}",
            "Content-Type": "application/json",
            "X-Title": self.settings.app_name,
        }

        try:
            async with httpx.AsyncClient(timeout=_TRANSCRIBE_TIMEOUT_S) as client:
                response = await client.post(
                    OPENROUTER_TRANSCRIPTIONS_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            logger.warning("OpenRouter transcription timed out (model=%s)", model)
            raise TranscribeError(
                "Transcription took too long. Try a shorter recording, or type "
                "your answer.",
                code="transcription_timeout",
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("OpenRouter transcription request failed")
            raise TranscribeError(
                "Could not reach transcription. Check your connection, or type "
                "your answer.",
                code="transcription_network",
            ) from exc

        if response.status_code >= 400:
            logger.warning(
                "OpenRouter transcription HTTP %s: %s",
                response.status_code,
                response.text[:500],
            )
            raise TranscribeError(
                "Could not transcribe that recording. Try again, or type your answer.",
                code="transcription_failed",
            )

        try:
            body = response.json()
        except ValueError as exc:
            logger.exception("OpenRouter transcription returned non-JSON")
            raise TranscribeError(
                "Could not transcribe that recording. Try again, or type your answer.",
                code="transcription_failed",
            ) from exc

        text = ""
        if isinstance(body, dict):
            raw = body.get("text")
            if isinstance(raw, str):
                text = raw.strip()

        if not text:
            raise TranscribeError(
                "No speech was detected. Try recording again closer to the mic, "
                "or type your answer.",
                code="empty_transcript",
            )
        return text


def _resolve_format(*, filename: str, content_type: str) -> str:
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in _MIME_TO_FORMAT:
        return _MIME_TO_FORMAT[mime]
    name = (filename or "").rsplit(".", 1)
    if len(name) == 2:
        ext = name[1].lower()
        if ext in _EXT_TO_FORMAT:
            return _EXT_TO_FORMAT[ext]
    return "webm"
