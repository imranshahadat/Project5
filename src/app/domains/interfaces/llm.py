from abc import ABC, abstractmethod
from typing import TypedDict


class Message(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class BaseLLM(ABC):
    """Port: any chat-completion provider must implement this."""

    @abstractmethod
    def generate(self, messages: list[Message]) -> str: ...
