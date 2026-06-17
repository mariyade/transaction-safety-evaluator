import pytest

from agents.transaction_safety.agent import TransactionSafetyAgent
from agents.transaction_safety.pydantic_models import AddressInput

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def agent():
    return TransactionSafetyAgent()


def test_agent_flow_returns_structured_result(agent):
    result, error = agent.run(
        AddressInput(
            address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain="ethereum",
        )
    )

    assert error is None
    assert result is not None
    assert result.verdict in ("SAFE", "FLAGGED", "UNKNOWN", "ESCALATE")
    assert 0 <= result.confidence <= 1
