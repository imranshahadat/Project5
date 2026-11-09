"""Adapter: UTF-8 text files -> BaseTextExtractor port."""

from app.domains.interfaces.extractor import BaseTextExtractor


class PlainTextExtractor(BaseTextExtractor):
    def extract(self, data: bytes, filename: str) -> str:
        return data.decode("utf-8", errors="replace").strip()
