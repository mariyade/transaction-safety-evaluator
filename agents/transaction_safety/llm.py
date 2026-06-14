from dataclasses import dataclass
from typing import Protocol
from openai import OpenAI
from agents.transaction_safety.config import OPENAI_API_KEY, TEMPERATURE
from agents.transaction_safety.tools import ToolCall


@dataclass(frozen=True)
class ToolLoopTurn:
    content: str | None
    tool_calls: list[ToolCall]
    assistant_message: dict


class LLMClient(Protocol):
    def complete(self, model: str, prompt: str) -> str: ...

    def complete_with_tools(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict],
    ) -> ToolLoopTurn: ...


class OpenAIChatClient:
    def __init__(
        self,
        api_key: str | None = OPENAI_API_KEY,
        timeout: float = 60.0,
        temperature: float = TEMPERATURE,
    ):
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self.temperature = temperature

    def complete(self, model: str, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def complete_with_tools(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict],
    ) -> ToolLoopTurn:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=self.temperature,
        )
        message = response.choices[0].message
        tool_calls = [
            ToolCall.from_openai(tool_call)
            for tool_call in (message.tool_calls or [])
        ]
        return ToolLoopTurn(
            content=message.content,
            tool_calls=tool_calls,
            assistant_message=message.model_dump(),
        )
