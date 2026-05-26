import pytest

from agents.transaction_safety.guardrails.crypto_secrets_guard import CryptoSecretsGuard

pytestmark = pytest.mark.guardrails


class TestCryptoSecretsGuard:
    def setup_method(self):
        self.guard = CryptoSecretsGuard()

    def test_clean_ethereum_address_passes(self):
        # 40-char hex address — NOT a private key (which is 64 chars)
        result = self.guard.check("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
        assert result.passed

    def test_clean_solana_address_passes(self):
        result = self.guard.check("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        assert result.passed

    def test_clean_freetext_passes(self):
        result = self.guard.check("Should I approve this DeFi contract on Ethereum?")
        assert result.passed

    def test_eth_private_key_blocked(self):
        fake_key = "a" * 64
        result = self.guard.check(f"My private key is {fake_key}")
        assert not result.passed
        assert "private key" in result.error.lower()

    def test_eth_private_key_with_0x_prefix_blocked(self):
        fake_key = "0x" + "b" * 64
        result = self.guard.check(fake_key)
        assert not result.passed

    def test_wif_private_key_blocked(self):
        fake_wif = "5" + "K" * 51
        result = self.guard.check(f"WIF key: {fake_wif}")
        assert not result.passed

    def test_seed_phrase_12_words_blocked(self):
        seed = "abandon ability able about above absent absorb abstract absurd abuse access accident"
        result = self.guard.check(seed)
        assert not result.passed
        assert "seed phrase" in result.error.lower()

    def test_seed_phrase_24_words_blocked(self):
        seed = (
            "abandon ability able about above absent absorb abstract absurd abuse access accident "
            "account accuse achieve acid acoustic acquire across act action actor actress actual"
        )
        result = self.guard.check(seed)
        assert not result.passed

    def test_seed_phrase_embedded_in_text_blocked(self):
        seed = "abandon ability able about above absent absorb abstract absurd abuse access accident"
        result = self.guard.check(f"Please check my wallet. My seed phrase is: {seed}")
        assert not result.passed

    def test_normal_sentence_not_flagged_as_seed(self):
        result = self.guard.check(
            "The quick brown fox jumped over the lazy dog. This is a normal sentence."
        )
        assert result.passed

    def test_eleven_words_not_enough_for_seed(self):
        words = "abandon ability able about above absent absorb abstract absurd abuse access"
        result = self.guard.check(words)
        assert result.passed
