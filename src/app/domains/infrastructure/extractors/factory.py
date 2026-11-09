"""Dispatch a text extractor by file extension."""

from app.core.exceptions import UnsupportedFileTypeError
from app.domains.infrastructure.extractors.pypdf import PypdfTextExtractor
from app.domains.infrastructure.extractors.plain_text import PlainTextExtractor
from app.domains.interfaces.extractor import BaseTextExtractor
from app.domains.infrastructure.extractors.docx import DocxTextExtractor

# stateless singletons — one instance per file type
EXTRACTOR_REGISTRY: dict[str, BaseTextExtractor] = {
    "pdf": PypdfTextExtractor(),
    "txt": PlainTextExtractor(),
    "md": PlainTextExtractor(),
    "docx": DocxTextExtractor(),
}


def get_extractor(filename: str) -> BaseTextExtractor:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    extractor = EXTRACTOR_REGISTRY.get(ext)
    if extractor is None:
        raise UnsupportedFileTypeError(
            f"No extractor for '.{ext}'. Supported: {', '.join(EXTRACTOR_REGISTRY)}"
        )
    return extractor
