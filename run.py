from agents.transaction_safety.agent import TransactionSafetyAgent
from agents.transaction_safety.logger import get_logger
from agents.transaction_safety.pydantic_models import AddressInput, FreeTextInput

logger = get_logger(__name__)

agent = TransactionSafetyAgent()

STRUCTURED_CASES = [
    AddressInput(address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", chain="ethereum"),
    # AddressInput(address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", chain="solana"),
]

COMPLEX_CASES = [
    FreeTextInput(
        text="Can I send USDC from Ethereum to a Solana address 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM?"
    ),
    FreeTextInput(text="A DeFi site wants unlimited USDC approval for 500% APY — is this safe?"),
    FreeTextInput(
        text="Someone sent me a link to claim free USDC by approving a contract. Should I do it?"
    ),
]

for case in STRUCTURED_CASES:
    label = getattr(case, "address", None) or case.text[:100]
    logger.info("=== %s ===", label)
    result, error = agent.run(case)
    if error:
        logger.error("result: %s", error)
    else:
        logger.info("result:\n%s", result.model_dump_json(indent=2))
