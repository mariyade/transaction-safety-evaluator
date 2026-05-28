from abc import ABC, abstractmethod

from openai import OpenAI

from framework.core.config import OPENAI_API_KEY
from framework.core.logger import get_logger
from framework.core.schemas import BaseAgentInput, BaseAgentOutput

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base — every agent gets the OpenAI client, tool loop, and LLM call for free."""

    def __init__(self, model: str, max_tool_rounds: int = 5):
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @property
    @abstractmethod
    def tools_schema(self) -> list: ...

    @abstractmethod
    def _handle_tool_call(self, tool_call) -> str: ...

    @abstractmethod
    def run(self, input: BaseAgentInput) -> tuple[BaseAgentOutput | None, str | None]: ...

    def _call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def _run_tool_loop(self, user_message: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _ in range(self.max_tool_rounds):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools_schema,
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump())

            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    logger.info("tool call — %s", tool_call.function.name)
                    messages.append({
                        "role": "tool",
                        "content": self._handle_tool_call(tool_call),
                        "tool_call_id": tool_call.id,
                    })
            else:
                return msg.content

        raise RuntimeError(f"Tool loop exceeded {self.max_tool_rounds} rounds")
