"""Adapter: python-docx -> BaseTextExtractor port (.docx -> text)."""

import io

from app.core.exceptions import TextExtractionError
from app.domains.interfaces.extractor import BaseTextExtractor


class DocxTextExtractor(BaseTextExtractor):
    def extract(self, data: bytes, filename: str) -> str:
        try:
            from docx import Document  # python-docx
        except ImportError as e:
            raise TextExtractionError(
                "python-docx is not installed — run: pip install python-docx"
            ) from e
        document = Document(io.BytesIO(data))
        parts = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n\n".join(parts).strip()
