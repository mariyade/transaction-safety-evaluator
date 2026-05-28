import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from agents.transaction_safety import tools
from agents.transaction_safety.schemas import AssessRiskArgs, RetrieveDocsArgs

pytestmark = pytest.mark.unit


def _tool_call(name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        )
    )


def test_assess_risk_flags_free_token_approval():
    result = tools.tool_assess_risk(AssessRiskArgs(
        address="unknown",
        chain="unknown",
        context="Someone sent me a link to claim free USDC by approving a contract.",
    ))

    assert "RISK ASSESSMENT" in result
    assert "free token claim" in result
    assert "contract approval" in result


def test_assess_risk_returns_safe_message_when_no_pattern_matches():
    result = tools.tool_assess_risk(AssessRiskArgs(
        address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        chain="ethereum",
    ))

    assert "No known high-risk patterns detected" in result


def test_retrieve_docs_formats_multiple_chunks(monkeypatch):
    monkeypatch.setattr(
        tools,
        "retrieve",
        lambda query: [
            {"page_content": f"{query} first chunk"},
            {"page_content": "second chunk"},
        ],
    )

    result = tools.tool_retrieve_docs(RetrieveDocsArgs(query="ethereum"))

    assert result == "ethereum first chunk\n\n---\n\nsecond chunk"


def test_handle_tool_call_validates_and_dispatches_assess_risk():
    result = tools.handle_tool_call(_tool_call(
        "assess_risk",
        {
            "address": "unknown",
            "chain": "unknown",
            "context": "A site promises guaranteed return if I send ETH first.",
        },
    ))

    assert "Guaranteed return" in result
    assert "Send first to receive" in result


def test_handle_tool_call_returns_unknown_tool_message():
    result = tools.handle_tool_call(_tool_call("not_a_tool", {}))

    assert result == "Unknown tool: not_a_tool"


def test_handle_tool_call_raises_for_invalid_tool_args():
    with pytest.raises(ValidationError):
        tools.handle_tool_call(_tool_call("assess_risk", {"chain": "ethereum"}))


def test_tools_schema_matches_registered_tools():
    schema_names = {tool["function"]["name"] for tool in tools.TOOLS_SCHEMA}

    assert schema_names == set(tools.TOOLS)
