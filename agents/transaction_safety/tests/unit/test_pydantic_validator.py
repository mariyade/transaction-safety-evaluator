import json
import pytest

from agents.transaction_safety.schemas import AddressValidationResult

pytestmark = pytest.mark.unit
from framework.core.pydantic_validator import create_retry_prompt, validate_llm_response, validate_with_model

VALID_RESPONSE = json.dumps({
    "verdict": "SAFE",
    "confidence": 0.95,
    "detected_format": "ERC-20",
    "reasoning": "No risk found.",
    "risk_factors": [],
})

INVALID_RESPONSE = "this is not json"


class TestValidateWithModel:
    def test_valid_json_returns_model(self):
        result, error = validate_with_model(AddressValidationResult, VALID_RESPONSE)
        assert result is not None
        assert error is None
        assert result.verdict == "SAFE"

    def test_invalid_json_returns_error(self):
        result, error = validate_with_model(AddressValidationResult, INVALID_RESPONSE)
        assert result is None
        assert error is not None

    def test_missing_required_fields_returns_error(self):
        result, error = validate_with_model(AddressValidationResult, json.dumps({"verdict": "SAFE"}))
        assert result is None
        assert "validation error" in error.lower()


class TestCreateRetryPrompt:
    def test_contains_original_prompt(self):
        prompt = create_retry_prompt("original", "bad response", "some error", AddressValidationResult)
        assert "original" in prompt

    def test_contains_error_message(self):
        prompt = create_retry_prompt("original", "bad response", "some error", AddressValidationResult)
        assert "some error" in prompt

    def test_contains_schema(self):
        prompt = create_retry_prompt("original", "bad response", "some error", AddressValidationResult)
        assert "verdict" in prompt
        assert "confidence" in prompt


class TestValidateLlmResponse:
    def test_succeeds_on_first_attempt(self):
        result, error = validate_llm_response(
            prompt="evaluate this",
            data_model=AddressValidationResult,
            call_llm_fn=lambda _: VALID_RESPONSE,
            n_retry=3,
        )
        assert result is not None
        assert error is None

    def test_retries_and_succeeds(self):
        attempts = {"count": 0}

        def flaky_llm(prompt):
            attempts["count"] += 1
            if attempts["count"] < 3:
                return INVALID_RESPONSE
            return VALID_RESPONSE

        result, error = validate_llm_response(
            prompt="evaluate this",
            data_model=AddressValidationResult,
            call_llm_fn=flaky_llm,
            n_retry=5,
        )
        assert result is not None
        assert error is None
        assert attempts["count"] == 3

    def test_exceeds_retries_returns_error(self):
        result, error = validate_llm_response(
            prompt="evaluate this",
            data_model=AddressValidationResult,
            call_llm_fn=lambda _: INVALID_RESPONSE,
            n_retry=2,
        )
        assert result is None
        assert "Max retries reached" in error
