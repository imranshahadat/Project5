from abc import ABC, abstractmethod


class BaseTextExtractor(ABC):
    """Port: turn raw file bytes into plain text."""

    @abstractmethod
    def extract(self, data: bytes, filename: str) -> str: ...
