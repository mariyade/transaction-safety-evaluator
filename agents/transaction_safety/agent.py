from agents.transaction_safety.config import MODEL, N_RETRY
from agents.transaction_safety.guardrails import (
    CryptoSecretsGuard,
    HallucinationGuard,
    PromptInjectionGuard,
    VerdictGuard,
)
from agents.transaction_safety.prompts import SYSTEM_PROMPT, build_structured_output_prompt
from agents.transaction_safety.schemas import AddressInput, AddressValidationResult
from agents.transaction_safety.tools import TOOLS_SCHEMA, handle_tool_call
from framework.core.base_agent import BaseAgent
from framework.core.guardrails import PIIGuard
from framework.core.logger import get_logger
from framework.core.pydantic_validator import validate_llm_response
from framework.core.schemas import FreeTextInput

logger = get_logger(__name__)


class TransactionSafetyAgent(BaseAgent):

    def __init__(self, model: str = MODEL):
        super().__init__(model)
        self._input_guards = [
            PromptInjectionGuard(),
            PIIGuard(),
            CryptoSecretsGuard(),
        ]
        self._output_guard = VerdictGuard()
        self._hallucination_guard = HallucinationGuard()
        self._assess_risk_results: list[str] = []

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def tools_schema(self) -> list:
        return TOOLS_SCHEMA

    def _handle_tool_call(self, tool_call) -> str:
        result = handle_tool_call(tool_call)
        if tool_call.function.name == "assess_risk":
            self._assess_risk_results.append(result)
        return result

    def run(self, input: AddressInput | FreeTextInput) -> tuple[AddressValidationResult | None, str | None]:
        if isinstance(input, AddressInput):
            user_message = f"Evaluate this address: {input.address} on {input.chain}"
            address, chain = input.address, input.chain
        else:
            user_message = input.text
            address, chain = "unknown", "unknown"

        logger.info("run started — %s", user_message[:80])
        self._assess_risk_results = []

        guards = self._input_guards if isinstance(input, FreeTextInput) else [
            g for g in self._input_guards if not isinstance(g, PIIGuard)
        ]
        for guard in guards:
            guard_result = guard.check(user_message)
            if not guard_result.passed:
                logger.warning("input guard blocked — %s", guard_result.error)
                return None, guard_result.error

        agent_response = self._run_tool_loop(user_message)
        structured_prompt = build_structured_output_prompt(address, chain, agent_response)
        result, error = validate_llm_response(
            prompt=structured_prompt,
            data_model=AddressValidationResult,
            call_llm_fn=self._call_llm,
            n_retry=N_RETRY,
        )

        if error:
            logger.error("run failed — %s", error)
            return None, error

        guard_result = self._output_guard.check(result)
        if not guard_result.passed:
            logger.warning("output guard blocked — %s", guard_result.error)
            return None, guard_result.error

        # Only assess_risk results are factual claims about this specific address
        full_context = "\n\n".join(self._assess_risk_results)
        guard_result = self._hallucination_guard.check(
            reasoning=result.reasoning,
            context=full_context,
        )
        if not guard_result.passed:
            logger.warning("hallucination guard blocked — %s", guard_result.error)
            return None, guard_result.error

        logger.info("run complete — verdict=%s confidence=%s", result.verdict, result.confidence)
        return result, None
