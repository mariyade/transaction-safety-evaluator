import re

from framework.core.guardrails.base import GuardResult
from framework.core.logger import get_logger

logger = get_logger(__name__)

# Ethereum/EVM private key: exactly 64 hex chars, optionally 0x-prefixed.
# Deliberately excludes 0x + 40-char addresses (length is different).
_ETH_PRIVATE_KEY = re.compile(r'(?:0x)?[0-9a-fA-F]{64}(?![0-9a-fA-F])')

# Bitcoin WIF private key: starts with 5, K, or L followed by 50-51 base58 chars
_WIF_KEY = re.compile(r'\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b')

# Solana private key: base58-encoded 64-byte key is typically 86-88 chars.
# Solana addresses are 32-44 chars, so this range avoids false positives.
_SOL_PRIVATE_KEY = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{86,88}\b')

# Matches a single pure lowercase word of 3-8 letters (BIP-39 word shape)
_BIP39_WORD = re.compile(r'^[a-z]{3,8}$')

# Valid BIP-39 seed phrase lengths
_SEED_LENGTHS = {12, 15, 18, 21, 24}


def _contains_seed_phrase(text: str) -> bool:
    """Return True if the text contains a sequence of 12/15/18/21/24 consecutive
    lowercase words that all match the BIP-39 word shape (3-8 letters, no digits
    or punctuation). Splits on whitespace so punctuation-separated tokens break
    the run."""
    run = 0
    for token in text.lower().split():
        if _BIP39_WORD.match(token):
            run += 1
            if run in _SEED_LENGTHS:
                return True
        else:
            run = 0
    return False


class CryptoSecretsGuard:
    """Detects blockchain-specific secrets: private keys and BIP-39 seed phrases.

    Specific to agents that handle crypto input. Use alongside PIIGuard for
    complete input coverage.
    """

    def check(self, text: str) -> GuardResult:
        if _ETH_PRIVATE_KEY.search(text):
            logger.warning("potential Ethereum/EVM private key in input")
            return GuardResult(passed=False, error="Potential private key detected in input")

        if _WIF_KEY.search(text):
            logger.warning("potential WIF private key in input")
            return GuardResult(passed=False, error="Potential private key detected in input")

        if _SOL_PRIVATE_KEY.search(text):
            logger.warning("potential Solana private key in input")
            return GuardResult(passed=False, error="Potential private key detected in input")

        if _contains_seed_phrase(text):
            logger.warning("potential BIP-39 seed phrase in input")
            return GuardResult(passed=False, error="Potential seed phrase detected in input")

        return GuardResult(passed=True)
