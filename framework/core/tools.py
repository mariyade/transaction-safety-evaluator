from collections.abc import Callable
from dataclasses import dataclass

from framework.core.schemas import BaseToolArgs

ToolHandler = Callable[[BaseToolArgs], str]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: str
    id: str | None = None

    @classmethod
    def from_openai(cls, tool_call) -> "ToolCall":
        return cls(
            name=tool_call.function.name,
            arguments=tool_call.function.arguments,
            id=tool_call.id,
        )


@dataclass(frozen=True)
class ToolDefinition:
    description: str
    args_model: type[BaseToolArgs]
    handler: ToolHandler

    def schema(self, name: str) -> dict:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }

    def run(self, arguments: str) -> str:
        args = self.args_model.model_validate_json(arguments)
        return self.handler(args)


class ToolRegistry(dict[str, ToolDefinition]):
    @property
    def schema(self) -> list[dict]:
        return [tool.schema(name) for name, tool in self.items()]

    def handle_call(self, tool_call: ToolCall) -> str:
        tool = self.get(tool_call.name)
        if tool:
            return tool.run(tool_call.arguments)
        return f"Unknown tool: {tool_call.name}"
