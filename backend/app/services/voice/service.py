"""
Voice service: speech-to-text transcription via Whisper.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.schemas import TranscriptionResponse

logger = get_logger(__name__)
settings = get_settings()

# Lazy-load whisper to avoid import overhead at startup
_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(settings.whisper_model)
        logger.info("Whisper model loaded", model=settings.whisper_model)
    return _whisper_model


class VoiceService:
    """Handles speech-to-text transcription."""

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> TranscriptionResponse:
        """Transcribe audio bytes to text."""
        start = time.perf_counter()

        # Write to temp file (Whisper requires file path)
        suffix = Path(filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            model = _get_whisper()
            result = model.transcribe(
                temp_path,
                language=None,  # auto-detect
                task="transcribe",
            )

            duration = time.perf_counter() - start
            text = result.get("text", "").strip()
            language = result.get("language", "en")

            logger.info(
                "Transcription complete",
                language=language,
                duration_s=round(duration, 2),
                text_len=len(text),
            )

            return TranscriptionResponse(
                text=text,
                language=language,
                duration_seconds=round(duration, 2),
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)


voice_service = VoiceService()
