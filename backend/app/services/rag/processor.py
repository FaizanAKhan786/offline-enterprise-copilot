"""
Document processing pipeline: extraction, chunking, embedding, indexing.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TextChunk:
    """Represents a chunk of text with metadata."""

    __slots__ = ("text", "metadata", "embedding")

    def __init__(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        self.text = text
        self.metadata = metadata or {}
        self.embedding: list[float] | None = None

    def __repr__(self) -> str:
        return f"TextChunk(len={len(self.text)}, page={self.metadata.get('page')})"


class DocumentProcessor:
    """Handles extraction, OCR, and chunking for uploaded documents."""

    SUPPORTED_TYPES = {
        "application/pdf": "_extract_pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "_extract_docx",
        "text/plain": "_extract_text",
        "image/png": "_extract_image_ocr",
        "image/jpeg": "_extract_image_ocr",
        "image/tiff": "_extract_image_ocr",
    }

    def __init__(self) -> None:
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    async def process(
        self,
        file_path: str | Path,
        content_type: str,
        document_id: str,
        filename: str,
    ) -> list[TextChunk]:
        """Full pipeline: extract → chunk → return with metadata."""
        file_path = Path(file_path)
        handler_name = self.SUPPORTED_TYPES.get(content_type)
        if not handler_name:
            raise ValueError(f"Unsupported content type: {content_type}")

        handler = getattr(self, handler_name)
        pages: list[dict[str, Any]] = handler(file_path)

        chunks: list[TextChunk] = []
        for page in pages:
            text = page["text"].strip()
            if not text:
                continue
            page_chunks = self._chunk_text(text)
            for i, chunk_text in enumerate(page_chunks):
                chunk = TextChunk(
                    text=chunk_text,
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "page": page.get("page", 0),
                        "chunk_index": i,
                        "content_hash": hashlib.md5(chunk_text.encode()).hexdigest(),
                    },
                )
                chunks.append(chunk)

        logger.info(
            "Document processed",
            document_id=document_id,
            filename=filename,
            pages=len(pages),
            chunks=len(chunks),
        )
        return chunks

    def _extract_pdf(self, path: Path) -> list[dict[str, Any]]:
        """Extract text from PDF, with OCR fallback for scanned pages."""
        pages = []
        doc = fitz.open(str(path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            # OCR fallback for scanned/image-only pages
            if len(text.strip()) < 50:
                text = self._ocr_page(page)

            pages.append({"page": page_num + 1, "text": text})
        doc.close()
        return pages

    def _extract_docx(self, path: Path) -> list[dict[str, Any]]:
        doc = DocxDocument(str(path))
        full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return [{"page": 1, "text": full_text}]

    def _extract_text(self, path: Path) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8", errors="replace")
        return [{"page": 1, "text": text}]

    def _extract_image_ocr(self, path: Path) -> list[dict[str, Any]]:
        """OCR an image file using Tesseract."""
        try:
            import pytesseract
            image = Image.open(path)
            text = pytesseract.image_to_string(image, lang="eng+ara+hin")
            return [{"page": 1, "text": text}]
        except Exception as e:
            logger.error("OCR failed", path=str(path), error=str(e))
            return [{"page": 1, "text": ""}]

    def _ocr_page(self, page: fitz.Page) -> str:
        """OCR a single PDF page by rendering to image."""
        try:
            import pytesseract
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            return pytesseract.image_to_string(img, lang="eng+ara+hin")
        except Exception as e:
            logger.warning("Page OCR failed", error=str(e))
            return ""

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks by character count with sentence boundaries."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                for sep in (". ", ".\n", "\n\n", "\n", " "):
                    boundary = text.rfind(sep, start + self.chunk_size // 2, end)
                    if boundary != -1:
                        end = boundary + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return chunks


document_processor = DocumentProcessor()
