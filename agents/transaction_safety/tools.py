import re
from collections.abc import Callable
from dataclasses import dataclass

from agents.transaction_safety.knowledge_base import retrieve
from agents.transaction_safety.logger import get_logger
from agents.transaction_safety.pydantic_models import AssessRiskArgs, BaseToolArgs, RetrieveDocsArgs

logger = get_logger(__name__)


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
    handler: Callable[[BaseToolArgs], str]

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

    def run_tool_call(self, tool_call: ToolCall) -> str:
        tool = self.get(tool_call.name)
        if tool:
            return tool.run(tool_call.arguments)
        return f"Unknown tool: {tool_call.name}"


RISKY_PATTERNS = [
    (r"unlimited|max uint256", "CRITICAL: Unlimited token approval detected."),
    (r"setapprovalforall", "CRITICAL: setApprovalForAll — commonly used in phishing attacks."),
    (r"airdrop.*claim|free.*mint|claim.*free|free.*usdc|free.*token", "HIGH: Unsolicited free token claim — common phishing."),
    (r"approv.*contract|link.*approv|sign.*contract", "CRITICAL: Unsolicited contract approval request — common drain attack."),
    (r"double|2x|guaranteed return", "CRITICAL: Guaranteed return promise — scam pattern."),
    (r"send.*first|deposit.*first", "CRITICAL: 'Send first to receive' — always a scam."),
]


def tool_retrieve_docs(args: RetrieveDocsArgs) -> str:
    docs = retrieve(args.query)
    result = "\n\n---\n\n".join(doc["page_content"] for doc in docs)
    logger.debug("retrieve_docs query='%s' returned:\n%s", args.query, result)
    return result


def _risk_scan_text(args: AssessRiskArgs) -> str:
    parts = [
        f"address={args.address}",
        f"chain={args.chain}",
    ]
    if args.context:
        parts.append(f"context={args.context}")
    return " ".join(parts).lower()


def _format_findings(findings: list[str]) -> str:
    if not findings:
        return "No known high-risk patterns detected. Verify the address independently before proceeding."
    return "RISK ASSESSMENT — Issues Found:\n" + "\n".join(f"- {finding}" for finding in findings)


def tool_assess_risk(args: AssessRiskArgs) -> str:
    scan_text = _risk_scan_text(args)
    findings = [
        message
        for pattern, message in RISKY_PATTERNS
        if re.search(pattern, scan_text)
    ]
    return _format_findings(findings)


TOOLS = ToolRegistry({
    "retrieve_docs": ToolDefinition(
        description="Retrieve documentation about address formats for a given blockchain.",
        args_model=RetrieveDocsArgs,
        handler=tool_retrieve_docs,
    ),
    "assess_risk": ToolDefinition(
        description="Assess a blockchain address for known scam and phishing patterns.",
        args_model=AssessRiskArgs,
        handler=tool_assess_risk,
    ),
})

TOOLS_SCHEMA = TOOLS.schema


def execute_tool_call(tool_call: ToolCall) -> str:
    """Validate tool args through Pydantic, then execute the tool."""
    return TOOLS.run_tool_call(tool_call)
