import pytest
from pydantic import ValidationError

from agents.transaction_safety.schemas import AddressInput, AddressValidationResult, RiskFactor


class TestAddressInput:
    def test_valid_ethereum_address(self):
        i = AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="ethereum")
        assert i.address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    def test_valid_solana_address(self):
        i = AddressInput(address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", chain="solana")
        assert i.chain == "solana"

    def test_chain_is_lowercased(self):
        i = AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="Ethereum")
        assert i.chain == "ethereum"

    def test_address_is_stripped(self):
        i = AddressInput(address="  0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48  ", chain="ethereum")
        assert i.address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    def test_invalid_ethereum_address_too_short(self):
        with pytest.raises(ValidationError, match="exactly 40 hex characters"):
            AddressInput(address="0xABCD", chain="ethereum")

    def test_invalid_ethereum_address_bad_chars(self):
        with pytest.raises(ValidationError, match="exactly 40 hex characters"):
            AddressInput(address="0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG", chain="ethereum")

    def test_unsupported_chain(self):
        with pytest.raises(ValidationError, match="Unsupported chain"):
            AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="bitcon")

    def test_default_address_type(self):
        i = AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="ethereum")
        assert i.address_type == "unknown"

    def test_request_id_is_auto_generated(self):
        i = AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="ethereum")
        assert i.request_id is not None

    def test_two_inputs_have_different_request_ids(self):
        a = AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="ethereum")
        b = AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="ethereum")
        assert a.request_id != b.request_id


class TestAddressValidationResult:
    def test_valid_safe_result(self):
        r = AddressValidationResult(
            verdict="SAFE",
            confidence=0.95,
            detected_format="ERC-20",
            reasoning="No risk found.",
        )
        assert r.verdict == "SAFE"

    def test_flagged_requires_risk_factors(self):
        with pytest.raises(ValidationError, match="risk_factors is empty"):
            AddressValidationResult(
                verdict="FLAGGED",
                confidence=0.9,
                detected_format="ERC-20",
                reasoning="Risky.",
                risk_factors=[],
            )

    def test_flagged_with_risk_factors_is_valid(self):
        r = AddressValidationResult(
            verdict="FLAGGED",
            confidence=0.9,
            detected_format="ERC-20",
            reasoning="Risky.",
            risk_factors=[RiskFactor(type="phishing", description="Fake airdrop.")],
        )
        assert len(r.risk_factors) == 1

    def test_confidence_below_zero(self):
        with pytest.raises(ValidationError, match="confidence must be between"):
            AddressValidationResult(
                verdict="SAFE", confidence=-0.1, detected_format="ERC-20", reasoning="x"
            )

    def test_confidence_above_one(self):
        with pytest.raises(ValidationError, match="confidence must be between"):
            AddressValidationResult(
                verdict="SAFE", confidence=1.1, detected_format="ERC-20", reasoning="x"
            )

    def test_confidence_is_rounded(self):
        r = AddressValidationResult(
            verdict="SAFE", confidence=0.123456789, detected_format="ERC-20", reasoning="x"
        )
        assert r.confidence == 0.1235

    def test_invalid_verdict(self):
        with pytest.raises(ValidationError):
            AddressValidationResult(
                verdict="MAYBE", confidence=0.5, detected_format="ERC-20", reasoning="x"
            )
