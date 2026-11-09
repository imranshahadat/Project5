"""Adapter: Vercel AI Gateway (OpenAI-compatible) -> BaseLLM port."""

from langchain_core.messages import convert_to_messages
from langchain_openai import ChatOpenAI

from app.core.config import AppSettings
from app.core.exceptions import APIKeyMissingError
from app.domains.interfaces.llm import BaseLLM, Message


class VercelLLM(BaseLLM):
    """One adapter serves every vendor — the model slug decides:

    'openai/gpt-4o-mini', 'anthropic/claude-...', 'cohere/...', ...
    """

    def __init__(self, settings: AppSettings) -> None:
        api_key = settings.vercel.api_key
        if not api_key or not api_key.get_secret_value():
            raise APIKeyMissingError("VERCEL_API_KEY is empty. Add it to your .env.")

        self._llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=api_key,
            base_url=settings.vercel.base_url,  # https://ai-gateway.vercel.sh/v1
            temperature=0.1,
        )

    def generate(self, messages: list[Message]) -> str:
        response = self._llm.invoke(convert_to_messages(messages))
        return str(response.content)
