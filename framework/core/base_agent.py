from abc import ABC, abstractmethod

from framework.core.llm import LLMClient, OpenAIChatClient
from framework.core.logger import get_logger
from framework.core.schemas import BaseAgentInput, BaseAgentOutput
from framework.core.tools import ToolCall

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base — every agent gets an LLM client, tool loop, and LLM call for free."""

    def __init__(
        self,
        model: str,
        max_tool_rounds: int = 5,
        llm_client: LLMClient | None = None,
    ):
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.llm_client = llm_client or OpenAIChatClient()

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @property
    @abstractmethod
    def tools_schema(self) -> list: ...

    @abstractmethod
    def _handle_tool_call(self, tool_call: ToolCall) -> str: ...

    @abstractmethod
    def run(self, input: BaseAgentInput) -> tuple[BaseAgentOutput | None, str | None]: ...

    def _call_llm(self, prompt: str) -> str:
        return self.llm_client.complete(model=self.model, prompt=prompt)

    def _run_tool_loop(self, user_message: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _ in range(self.max_tool_rounds):
            turn = self.llm_client.complete_with_tools(
                model=self.model,
                messages=messages,
                tools=self.tools_schema,
            )
            messages.append(turn.assistant_message)

            if turn.tool_calls:
                for tool_call in turn.tool_calls:
                    logger.info("tool call — %s", tool_call.name)
                    messages.append({
                        "role": "tool",
                        "content": self._handle_tool_call(tool_call),
                        "tool_call_id": tool_call.id,
                    })
            else:
                return turn.content or ""

        raise RuntimeError(f"Tool loop exceeded {self.max_tool_rounds} rounds")
