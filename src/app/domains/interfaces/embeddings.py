from abc import ABC, abstractmethod


class BaseEmbeddings(ABC):
    """Port: any embedding provider must implement this."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...
