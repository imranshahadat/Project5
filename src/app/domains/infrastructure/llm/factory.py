from typing import Optional

from app.core.config import AppSettings, get_settings
from app.core.exceptions import LLMProviderError
from app.domains.infrastructure._builder import build_provider
from app.domains.infrastructure.llm.vercel import VercelLLM
from app.domains.interfaces.llm import BaseLLM

LLM_REGISTRY: dict[str, type[BaseLLM]] = {
    "vercel": VercelLLM,
    # "aws_bedrock": BedrockLLM,   # <- future adapter goes here
}

API_KEY_REQUIREMENTS: dict[str, str] = {
    "vercel": "vercel.api_key",
}


def build_llm(settings: Optional[AppSettings] = None) -> BaseLLM:
    s = settings or get_settings()
    provider = s.llm_provider.value.lower()
    return build_provider(
        registry=LLM_REGISTRY,
        provider=provider,
        kind="LLM",
        api_key_path=API_KEY_REQUIREMENTS.get(provider),
        error=LLMProviderError,
        settings=s,
    )
