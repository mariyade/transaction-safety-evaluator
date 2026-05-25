from agents.transaction_safety.config import MODEL, N_RETRY
from agents.transaction_safety.prompts import SYSTEM_PROMPT, build_structured_output_prompt
from agents.transaction_safety.schemas import AddressInput, AddressValidationResult
from agents.transaction_safety.tools import TOOLS_SCHEMA, handle_tool_call
from framework.core.base_agent import BaseAgent
from framework.core.logger import get_logger
from framework.core.pydantic_validator import validate_llm_response
from framework.core.schemas import FreeTextInput

logger = get_logger(__name__)


class TransactionSafetyAgent(BaseAgent):

    def __init__(self, model: str = MODEL):
        super().__init__(model)

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def tools_schema(self) -> list:
        return TOOLS_SCHEMA

    def _handle_tool_call(self, tool_call) -> str:
        return handle_tool_call(tool_call)

    def run(self, input: AddressInput | FreeTextInput) -> tuple[AddressValidationResult | None, str | None]:
        if isinstance(input, AddressInput):
            user_message = f"Evaluate this address: {input.address} on {input.chain}"
            address, chain = input.address, input.chain
        else:
            user_message = input.text
            address, chain = "unknown", "unknown"

        logger.info("run started — %s", user_message[:80])
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
        else:
            logger.info("run complete — verdict=%s confidence=%s", result.verdict, result.confidence)
        return result, error
