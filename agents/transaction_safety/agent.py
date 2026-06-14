from agents.transaction_safety.config import MODEL, N_RETRY
from agents.transaction_safety.guardrails import (
    CryptoSecretsGuard,
    HallucinationGuard,
    PIIGuard,
    PromptInjectionGuard,
    VerdictGuard,
)
from agents.transaction_safety.llm import LLMClient, OpenAIChatClient
from agents.transaction_safety.logger import get_logger
from agents.transaction_safety.pydantic_validator import validate_response_with_retries
from agents.transaction_safety.prompts import SYSTEM_PROMPT
from agents.transaction_safety.schemas import AddressInput, AddressValidationResult, FreeTextInput
from agents.transaction_safety.tools import TOOLS_SCHEMA, execute_tool_call

logger = get_logger(__name__)

REQUIRED_TOOLS = {"retrieve_docs", "assess_risk"}


class TransactionSafetyAgent:

    def __init__(
        self,
        model: str = MODEL,
        max_tool_rounds: int = 5,
        llm_client: LLMClient | None = None,
    ):
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.llm_client = llm_client or OpenAIChatClient()
        self._input_guards = [
            PromptInjectionGuard(),
            PIIGuard(),
            CryptoSecretsGuard(),
        ]
        self._output_guard = VerdictGuard()
        self._hallucination_guard = HallucinationGuard()
        self._grounding_context: list[str] = []
        self._called_tools: set[str] = set()

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _escalate(self, reason: str) -> AddressValidationResult:
        return AddressValidationResult(
            verdict="ESCALATE",
            confidence=0.0,
            detected_format="unknown",
            reasoning=reason,
            risk_factors=[],
        )

    def _call_llm(self, prompt: str) -> str:
        return self.llm_client.complete(model=self.model, prompt=prompt)

    def _run_tool_loop(self, user_message: str) -> str:
        # Run the LLM with tools until it either returns a final answer or hits the round limit.
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _ in range(self.max_tool_rounds):
            turn = self.llm_client.complete_with_tools(
                model=self.model,
                messages=messages,
                tools=TOOLS_SCHEMA,
            )
            messages.append(turn.assistant_message)

            if not turn.tool_calls:
                return turn.content or ""

            for tool_call in turn.tool_calls:
                # Record required tool usage so the final response is based on retrieval and risk scanning.
                logger.info("tool call — %s", tool_call.name)
                self._called_tools.add(tool_call.name)
                tool_result = execute_tool_call(tool_call)
                if tool_call.name in REQUIRED_TOOLS:
                    self._grounding_context.append(tool_result)
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call.id,
                })

        raise RuntimeError(f"Tool loop exceeded {self.max_tool_rounds} rounds")

    def run(self, input: AddressInput | FreeTextInput) -> tuple[AddressValidationResult | None, str | None]:
        # Normalize supported input types into a single user message for the LLM.
        if isinstance(input, AddressInput):
            user_message = f"Evaluate this address: {input.address} on {input.chain}"
        else:
            user_message = input.text

        logger.info("run started — %s", user_message[:80])
        # Reset per-run state before tool calls start.
        self._grounding_context = []
        self._called_tools = set()

        # Block unsafe input before any LLM call.
        guards = self._input_guards if isinstance(input, FreeTextInput) else [
            g for g in self._input_guards if not isinstance(g, PIIGuard)
        ]
        for guard in guards:
            guard_result = guard.check(user_message)
            if not guard_result.passed:
                logger.warning("input guard blocked — %s", guard_result.error)
                return None, guard_result.error

        # Execute the LLM/tool workflow.
        try:
            agent_response = self._run_tool_loop(user_message)
        except RuntimeError as error:
            logger.error("tool loop failed — escalating — %s", error)
            return self._escalate(str(error)), None

        # Require both retrieval and risk scanning before trusting the final structured answer.
        missing_tools = REQUIRED_TOOLS - self._called_tools
        if missing_tools:
            reason = f"Required tool calls were skipped: {', '.join(sorted(missing_tools))}"
            logger.error("run failed — escalating — %s", reason)
            return self._escalate(reason), None

        # Validate the final tool-loop response as structured JSON; retry only if it is malformed.
        result, error = validate_response_with_retries(
            response_content=agent_response,
            retry_prompt_context=user_message,
            data_model=AddressValidationResult,
            call_llm_fn=self._call_llm,
            n_retry=N_RETRY,
        )

        if error:
            logger.error("run failed — escalating — %s", error)
            return self._escalate(error), None

        guard_result = self._output_guard.check(result)
        if not guard_result.passed:
            logger.warning("output guard failed — escalating — %s", guard_result.error)
            return self._escalate(guard_result.error), None

        # Check the final reasoning against the retrieved docs and deterministic risk scan.
        full_context = "\n\n".join(self._grounding_context)
        guard_result = self._hallucination_guard.check(
            reasoning=result.reasoning,
            context=full_context,
        )
        if not guard_result.passed:
            logger.warning("hallucination guard failed — escalating — %s", guard_result.error)
            return self._escalate(guard_result.error), None

        logger.info("run complete — verdict=%s confidence=%s", result.verdict, result.confidence)
        return result, None
