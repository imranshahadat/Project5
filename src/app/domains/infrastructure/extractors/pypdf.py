"""Adapter: pypdf -> BaseTextExtractor port (PDF -> text)."""

import io

from pypdf import PdfReader

from app.domains.interfaces.extractor import BaseTextExtractor


class PypdfTextExtractor(BaseTextExtractor):
    def extract(self, data: bytes, filename: str) -> str:
        reader = PdfReader(io.BytesIO(data))
        texts = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(texts).strip()
