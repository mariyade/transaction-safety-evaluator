import pytest

from agents.transaction_safety.agent import TransactionSafetyAgent
from agents.transaction_safety.schemas import AddressInput
from framework.core.schemas import FreeTextInput

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def agent():
    return TransactionSafetyAgent()


def test_valid_ethereum_address_is_safe(agent):
    result, error = agent.run(AddressInput(
        address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        chain="ethereum",
    ))
    assert error is None
    assert result.verdict == "SAFE"
    assert result.confidence > 0.7


def test_valid_solana_address_is_safe(agent):
    result, error = agent.run(AddressInput(
        address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        chain="solana",
    ))
    assert error is None
    assert result.verdict == "SAFE"
    assert result.detected_format == "Solana base58"


def test_solana_address_on_ethereum_is_flagged(agent):
    result, error = agent.run(AddressInput(
        address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        chain="ethereum",
    ))
    assert error is None
    assert result.verdict == "FLAGGED"
    assert len(result.risk_factors) > 0


def test_invalid_address_rejected_before_llm():
    with pytest.raises(Exception):
        AddressInput(address="not-an-address", chain="ethereum")


def test_free_text_scam_is_flagged(agent):
    result, error = agent.run(FreeTextInput(
        text="Someone sent me a link to claim free USDC by approving a contract. Should I do it?",
    ))
    assert error is None
    assert result.verdict == "FLAGGED"


def test_free_text_unlimited_approval_is_flagged(agent):
    result, error = agent.run(FreeTextInput(
        text="A DeFi site wants unlimited USDC approval for 500% APY — is this safe?",
    ))
    assert error is None
    assert result.verdict == "FLAGGED"
