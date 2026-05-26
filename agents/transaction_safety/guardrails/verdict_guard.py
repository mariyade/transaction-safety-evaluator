from framework.core.guardrails.base import GuardResult
from framework.core.logger import get_logger

logger = get_logger(__name__)

_VALID_VERDICTS = {"SAFE", "FLAGGED", "UNKNOWN"}


class VerdictGuard:
    """Output guard for AddressValidationResult.

    Checks rules that go beyond what Pydantic enforces at parse time:
    - FLAGGED verdict must carry at least one risk_factor
    - Risk factor descriptions must be non-trivial
    - Confidence must be plausible for the verdict
    """

    def check(self, result) -> GuardResult:
        if result.verdict not in _VALID_VERDICTS:
            return GuardResult(
                passed=False,
                error=f"Unexpected verdict '{result.verdict}'; must be one of {_VALID_VERDICTS}",
            )

        if result.verdict == "FLAGGED":
            if not result.risk_factors:
                logger.warning("output guard: FLAGGED verdict with no risk factors")
                return GuardResult(
                    passed=False,
                    error="FLAGGED verdict must include at least one risk factor",
                )
            for rf in result.risk_factors:
                if len(rf.description.strip()) < 10:
                    logger.warning("output guard: risk factor description too short — '%s'", rf.description)
                    return GuardResult(
                        passed=False,
                        error=f"Risk factor description is too vague: '{rf.description}'",
                    )

        if result.verdict == "FLAGGED" and result.confidence < 0.4:
            logger.warning("output guard: low confidence FLAGGED verdict (%s)", result.confidence)
            return GuardResult(
                passed=False,
                error=f"FLAGGED verdict with suspiciously low confidence ({result.confidence})",
            )

        return GuardResult(passed=True)
