"""
Translation service using LLM-based translation for multilingual support.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.services.llm.service import llm_service

logger = get_logger(__name__)

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ar": "Arabic",
    "hi": "Hindi",
}


class TranslationService:
    """Multilingual translation using the local LLM."""

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "ar",
        model: str | None = None,
    ) -> str:
        if source_lang == target_lang:
            return text

        source_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
        target_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

        prompt = (
            f"Translate the following text from {source_name} to {target_name}. "
            f"Output ONLY the translation, nothing else.\n\n{text}"
        )

        result = await llm_service.generate(
            prompt=prompt,
            model=model,
            temperature=0.2,
            max_tokens=len(text) * 3,
        )

        translated = result["content"].strip()
        logger.info(
            "Translation complete",
            source=source_lang,
            target=target_lang,
            input_len=len(text),
            output_len=len(translated),
        )
        return translated

    async def detect_language(self, text: str) -> str:
        prompt = (
            "Detect the language of the following text. "
            "Respond with ONLY the ISO 639-1 code (e.g., 'en', 'ar', 'hi').\n\n"
            f"{text[:500]}"
        )
        result = await llm_service.generate(prompt=prompt, temperature=0.0, max_tokens=5)
        lang = result["content"].strip().lower()[:2]
        return lang if lang in SUPPORTED_LANGUAGES else "en"


translation_service = TranslationService()
