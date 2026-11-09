"""Sliding-window chunking — pure domain logic, easy to unit test."""


def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Character window with overlap. CHUNK_SIZE / CHUNK_OVERLAP come from .env."""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    text = " ".join(text.split())  # normalise whitespace (PDF line breaks, etc.)
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while True:
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks
