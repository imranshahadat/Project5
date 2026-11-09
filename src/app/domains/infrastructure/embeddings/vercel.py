"""Adapter: Vercel AI Gateway /embeddings -> BaseEmbeddings port."""

from langchain_openai import OpenAIEmbeddings

from app.core.config import AppSettings
from app.core.exceptions import APIKeyMissingError
from app.domains.interfaces.embeddings import BaseEmbeddings


class VercelEmbeddings(BaseEmbeddings):
    def __init__(self, settings: AppSettings) -> None:
        api_key = settings.vercel.api_key
        if not api_key or not api_key.get_secret_value():
            raise APIKeyMissingError("VERCEL_API_KEY is empty. Add it to your .env.")

        self._embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,  # cohere/embed-v4.0
            api_key=api_key,
            base_url=settings.vercel.base_url,  # .../v1 -> /embeddings
            dimensions=settings.embedding_dimensions,
            check_embedding_ctx_length=False,  # don't tokenise with tiktoken for non-OpenAI models
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)
