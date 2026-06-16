import pytest

from agents.transaction_safety.guardrails.output.verdict_guard import VerdictGuard
from agents.transaction_safety.pydantic_models import AddressValidationResult, RiskFactor

pytestmark = [pytest.mark.unit, pytest.mark.guardrails]


def _make_result(**kwargs) -> AddressValidationResult:
    defaults = dict(
        verdict="SAFE",
        confidence=0.9,
        detected_format="ERC-20",
        reasoning="No risk patterns found.",
        risk_factors=[],
    )
    defaults.update(kwargs)
    return AddressValidationResult(**defaults)


class TestVerdictGuard:
    def setup_method(self):
        self.guard = VerdictGuard()

    def test_safe_verdict_passes(self):
        result = _make_result(verdict="SAFE", confidence=0.9)
        assert self.guard.check(result).passed

    def test_flagged_with_risk_factors_passes(self):
        result = _make_result(
            verdict="FLAGGED",
            confidence=0.85,
            risk_factors=[RiskFactor(type="phishing", description="Address matches known phishing contract")],
        )
        assert self.guard.check(result).passed

    def test_flagged_with_no_risk_factors_blocked_by_pydantic(self):
        # Pydantic's model_validator enforces this before VerdictGuard even sees it
        with pytest.raises(Exception):
            _make_result(verdict="FLAGGED", confidence=0.8, risk_factors=[])

    def test_flagged_with_trivial_description_blocked(self):
        result = _make_result(
            verdict="FLAGGED",
            confidence=0.8,
            risk_factors=[RiskFactor(type="scam", description="bad")],
        )
        guard_result = self.guard.check(result)
        assert not guard_result.passed
        assert "vague" in guard_result.error.lower()

    def test_flagged_low_confidence_blocked(self):
        result = _make_result(
            verdict="FLAGGED",
            confidence=0.3,
            risk_factors=[RiskFactor(type="phishing", description="Matches known phishing address list")],
        )
        guard_result = self.guard.check(result)
        assert not guard_result.passed
        assert "confidence" in guard_result.error.lower()

    def test_unknown_verdict_passes(self):
        result = _make_result(verdict="UNKNOWN", confidence=0.5)
        assert self.guard.check(result).passed

    def test_confidence_at_boundary_passes(self):
        result = _make_result(
            verdict="FLAGGED",
            confidence=0.4,
            risk_factors=[RiskFactor(type="format_anomaly", description="Solana address used on Ethereum chain")],
        )
        assert self.guard.check(result).passed

    def test_confidence_below_boundary_blocked(self):
        result = _make_result(
            verdict="FLAGGED",
            confidence=0.39,
            risk_factors=[RiskFactor(type="format_anomaly", description="Solana address used on Ethereum chain")],
        )
        assert not self.guard.check(result).passed
