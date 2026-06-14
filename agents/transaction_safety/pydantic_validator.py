import json
from typing import Callable, Optional, Type

from pydantic import BaseModel, ValidationError

from agents.transaction_safety.logger import get_logger

logger = get_logger(__name__)


def validate_with_model(
    data_model: Type[BaseModel],
    llm_response: str,
) -> tuple[Optional[BaseModel], Optional[str]]:
    """Try to parse an LLM response into a Pydantic model. Returns (data, None) or (None, error)."""
    try:
        validated_data = data_model.model_validate_json(llm_response)
        return validated_data, None
    except ValidationError as e:
        return None, f"This response generated a validation error: {e}"
    except Exception as e:
        return None, f"Failed to parse response as JSON: {e}"


def create_retry_prompt(
    original_prompt: str,
    original_response: str,
    error_message: str,
    data_model: Type[BaseModel],
) -> str:
    """Build a retry prompt with the original request, bad response, error, and required schema."""
    schema = json.dumps(data_model.model_json_schema(), indent=2)

    return f"""This is a request to fix an error in the structure of an llm_response.

Here is the original request:
<original_prompt>
{original_prompt}
</original_prompt>

Here is the original llm_response:
<llm_response>
{original_response}
</llm_response>

This response generated an error:
<error_message>
{error_message}
</error_message>

Compare the error message and the llm_response and identify what needs to be fixed.

Your response must match this exact JSON schema:
{schema}

Respond ONLY with valid JSON. Do not include any explanations or other text before or after the JSON object."""


def validate_llm_response(
    prompt: str,
    data_model: Type[BaseModel],
    call_llm_fn: Callable[[str], str],
    n_retry: int = 5,
) -> tuple[Optional[BaseModel], Optional[str]]:
    """Call an LLM, validate output against a Pydantic model, retry with error feedback on failure.

    call_llm_fn is injected so this works with any LLM provider.
    """
    response_content = call_llm_fn(prompt)
    return validate_response_with_retries(
        response_content=response_content,
        retry_prompt_context=prompt,
        data_model=data_model,
        call_llm_fn=call_llm_fn,
        n_retry=n_retry,
    )


def validate_response_with_retries(
    response_content: str,
    retry_prompt_context: str,
    data_model: Type[BaseModel],
    call_llm_fn: Callable[[str], str],
    n_retry: int = 5,
) -> tuple[Optional[BaseModel], Optional[str]]:
    """Validate an existing LLM response, calling the LLM again only to repair invalid JSON."""
    for attempt in range(n_retry + 1):
        validated_data, validation_error = validate_with_model(data_model, response_content)

        if validation_error:
            if attempt < n_retry:
                logger.warning("validation retry %d/%d — %s", attempt + 1, n_retry, validation_error)
                retry_prompt = create_retry_prompt(
                    original_prompt=retry_prompt_context,
                    original_response=response_content,
                    error_message=validation_error,
                    data_model=data_model,
                )
                response_content = call_llm_fn(retry_prompt)
                continue

            logger.error("max retries reached — %s", validation_error)
            return None, f"Max retries reached. Last error: {validation_error}"

        return validated_data, None

    return None, "Unexpected exit from retry loop"
