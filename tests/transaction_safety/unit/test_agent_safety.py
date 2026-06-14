from types import MethodType

import pytest

from agents.transaction_safety.agent import TransactionSafetyAgent
from agents.transaction_safety.schemas import AddressInput
from agents.transaction_safety.guardrails.base import GuardResult

pytestmark = pytest.mark.unit


class PassingGuard:
    def check(self, text: str) -> GuardResult:
        return GuardResult(passed=True)


def _agent_without_heavy_init() -> TransactionSafetyAgent:
    agent = TransactionSafetyAgent.__new__(TransactionSafetyAgent)
    agent._input_guards = [PassingGuard()]
    agent._grounding_context = []
    agent._called_tools = set()
    return agent


def test_missing_required_tools_escalates_before_structured_validation():
    agent = _agent_without_heavy_init()
    agent._run_tool_loop = MethodType(lambda self, message: "final answer without tools", agent)

    result, error = agent.run(AddressInput(
        address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        chain="ethereum",
    ))

    assert error is None
    assert result.verdict == "ESCALATE"
    assert "Required tool calls were skipped" in result.reasoning
    assert "assess_risk" in result.reasoning
    assert "retrieve_docs" in result.reasoning


def test_tool_loop_runtime_error_escalates():
    agent = _agent_without_heavy_init()

    def raise_tool_loop_error(self, message):
        raise RuntimeError("Tool loop exceeded 1 rounds")

    agent._run_tool_loop = MethodType(raise_tool_loop_error, agent)

    result, error = agent.run(AddressInput(
        address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        chain="ethereum",
    ))

    assert error is None
    assert result.verdict == "ESCALATE"
    assert result.reasoning == "Tool loop exceeded 1 rounds"
