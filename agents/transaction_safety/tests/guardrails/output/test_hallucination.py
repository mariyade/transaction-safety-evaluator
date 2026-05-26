import pytest

from agents.transaction_safety.guardrails.hallucination_guard import HallucinationGuard

pytestmark = pytest.mark.guardrails

# Mock NLI functions — inject instead of downloading the model
_ALWAYS_ENTAILS = lambda ctx, claim: {"entailment": 0.92, "neutral": 0.06, "contradiction": 0.02}
_ALWAYS_CONTRADICTS = lambda ctx, claim: {"entailment": 0.03, "neutral": 0.07, "contradiction": 0.90}
_ALWAYS_NEUTRAL = lambda ctx, claim: {"entailment": 0.05, "neutral": 0.90, "contradiction": 0.05}


class TestHallucinationGuard:
    def test_supported_reasoning_passes(self):
        guard = HallucinationGuard(nli_fn=_ALWAYS_ENTAILS)
        result = guard.check(
            reasoning="Ethereum addresses start with 0x followed by 40 hex characters.",
            context="Ethereum addresses use the 0x prefix with exactly 40 hexadecimal characters.",
        )
        assert result.passed

    def test_contradicting_reasoning_blocked(self):
        guard = HallucinationGuard(nli_fn=_ALWAYS_CONTRADICTS)
        result = guard.check(
            reasoning="This Solana address format is valid for Ethereum transactions.",
            context="Ethereum addresses use 0x prefix. Solana addresses use base58 encoding and are incompatible.",
        )
        assert not result.passed
        assert "contradicts" in result.error.lower()
        assert result.error is not None

    def test_neutral_reasoning_passes(self):
        # NEUTRAL means the context doesn't confirm or deny — allowed
        guard = HallucinationGuard(nli_fn=_ALWAYS_NEUTRAL)
        result = guard.check(
            reasoning="The address appears to follow standard format conventions.",
            context="Ethereum addresses use 0x prefix with 40 hex characters.",
        )
        assert result.passed

    def test_empty_context_skipped(self):
        guard = HallucinationGuard(nli_fn=_ALWAYS_CONTRADICTS)
        result = guard.check(
            reasoning="This is some reasoning about an address.",
            context="",
        )
        assert result.passed

    def test_empty_reasoning_skipped(self):
        guard = HallucinationGuard(nli_fn=_ALWAYS_CONTRADICTS)
        result = guard.check(
            reasoning="",
            context="Ethereum addresses use the 0x prefix.",
        )
        assert result.passed

    def test_short_sentences_skipped(self):
        # Sentences under 25 chars are not checked — too short to be claims
        guard = HallucinationGuard(nli_fn=_ALWAYS_CONTRADICTS)
        result = guard.check(
            reasoning="SAFE. No issues.",
            context="Ethereum addresses use the 0x prefix.",
        )
        assert result.passed

    def test_contradiction_threshold_respected(self):
        # Score of 0.80 is below default threshold of 0.85 — should pass
        mock_nli = lambda ctx, claim: {"entailment": 0.1, "neutral": 0.10, "contradiction": 0.80}
        guard = HallucinationGuard(contradiction_threshold=0.85, nli_fn=mock_nli)
        result = guard.check(
            reasoning="The address format appears to be standard for this blockchain.",
            context="Ethereum addresses use 0x prefix with 40 hex characters.",
        )
        assert result.passed

    def test_custom_threshold_catches_lower_score(self):
        mock_nli = lambda ctx, claim: {"entailment": 0.1, "neutral": 0.10, "contradiction": 0.80}
        guard = HallucinationGuard(contradiction_threshold=0.75, nli_fn=mock_nli)
        result = guard.check(
            reasoning="The address format appears to be standard for this blockchain.",
            context="Ethereum addresses use 0x prefix with 40 hex characters.",
        )
        assert not result.passed
