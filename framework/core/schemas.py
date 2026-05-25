import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class BaseAgentInput(BaseModel):
    """Base input — auto-generates request_id and timestamp for every request."""

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this request, auto-generated if not provided"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this request was created"
    )


class BaseAgentOutput(BaseModel):
    """Base output — every agent must return a verdict and confidence score."""

    verdict: str = Field(..., description="Outcome of the evaluation, e.g. SAFE, FLAGGED, CORRECT")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_valid(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class FreeTextInput(BaseAgentInput):
    text: str = Field(..., description="Free text input — question, scenario, or natural language query")


class BaseToolArgs(BaseModel):
    """Type marker for tool input schemas — subclasses generate OpenAI function definitions via model_json_schema()."""
    pass
