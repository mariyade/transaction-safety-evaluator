import re

from agents.transaction_safety.knowledge_base import retrieve
from agents.transaction_safety.schemas import AssessRiskArgs, RetrieveDocsArgs
from framework.core.logger import get_logger
from framework.core.tools import ToolCall, ToolDefinition, ToolRegistry

logger = get_logger(__name__)

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


def handle_tool_call(tool_call: ToolCall) -> str:
    """Validate tool args through Pydantic, then execute the tool."""
    return TOOLS.handle_call(tool_call)
