import re

from agents.transaction_safety.knowledge_base import retrieve
from agents.transaction_safety.schemas import AssessRiskArgs, RetrieveDocsArgs
from framework.core.logger import get_logger

logger = get_logger(__name__)

RISKY_PATTERNS = [
    (r"unlimited|max uint256", "CRITICAL: Unlimited token approval detected."),
    (r"setapprovalforall", "CRITICAL: setApprovalForAll — commonly used in phishing attacks."),
    (r"airdrop.*claim|free.*mint", "HIGH: Airdrop/free mint pattern — common phishing."),
    (r"double|2x|guaranteed return", "CRITICAL: Guaranteed return promise — scam pattern."),
    (r"send.*first|deposit.*first", "CRITICAL: 'Send first to receive' — always a scam."),
]

# Tool schemas generated from Pydantic models 
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_docs",
            "description": "Retrieve documentation about address formats for a given blockchain.",
            "parameters": RetrieveDocsArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assess_risk",
            "description": "Assess a blockchain address for known scam and phishing patterns.",
            "parameters": AssessRiskArgs.model_json_schema(),
        },
    },
]


def tool_retrieve_docs(args: RetrieveDocsArgs) -> str:
    docs = retrieve(args.query)
    result = "\n\n---\n\n".join(doc["page_content"] for doc in docs)
    logger.debug("retrieve_docs query='%s' returned:\n%s", args.query, result)
    return result


def tool_assess_risk(args: AssessRiskArgs) -> str:
    details = f"address={args.address} chain={args.chain}"
    if args.context:
        details += f" context={args.context}"

    findings = [
        msg for pattern, msg in RISKY_PATTERNS
        if re.search(pattern, details.lower())
    ]

    if not findings:
        return "No known high-risk patterns detected. Verify the address independently before proceeding."
    return "RISK ASSESSMENT — Issues Found:\n" + "\n".join(f"- {f}" for f in findings)


def handle_tool_call(tool_call) -> str:
    """Validate tool args through Pydantic, then execute the tool."""
    name = tool_call.function.name
    if name == "retrieve_docs":
        args = RetrieveDocsArgs.model_validate_json(tool_call.function.arguments)
        return tool_retrieve_docs(args)
    if name == "assess_risk":
        args = AssessRiskArgs.model_validate_json(tool_call.function.arguments)
        return tool_assess_risk(args)
    return f"Unknown tool: {name}"
