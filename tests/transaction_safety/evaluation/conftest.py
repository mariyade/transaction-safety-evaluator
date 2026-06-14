import pytest

from agents.transaction_safety.agent import TransactionSafetyAgent


@pytest.fixture(scope="session")
def agent():
    return TransactionSafetyAgent()
