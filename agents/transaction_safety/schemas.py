import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from framework.core.schemas import BaseAgentInput, BaseAgentOutput, BaseToolArgs


RiskVerdict = Literal["SAFE", "FLAGGED", "UNKNOWN", "ESCALATE"]

SUPPORTED_CHAINS = {"ethereum", "polygon", "arbitrum", "optimism", "base", "solana"}


class AddressInput(BaseAgentInput):
    address: str = Field(..., description="Blockchain wallet or contract address to evaluate")
    chain: str = Field(..., description=f"Blockchain network. Supported: {', '.join(sorted(SUPPORTED_CHAINS))}")
    address_type: Literal["wallet", "contract", "unknown"] = Field(
        "unknown",
        description="Whether this is a wallet address, a smart contract, or unknown"
    )

    @field_validator("address")
    @classmethod
    def validate_address_format(cls, address: str) -> str:
        address = address.strip()
        if re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
            return address
        if re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", address):
            return address
        raise ValueError(
            "Address must be a valid Ethereum address (0x + 40 hex chars) "
            "or Solana address (32-44 base58 chars)"
        )

    @field_validator("chain")
    @classmethod
    def validate_chain(cls, chain: str) -> str:
        chain = chain.lower().strip()
        if chain not in SUPPORTED_CHAINS:
            raise ValueError(
                f"Unsupported chain '{chain}'. Must be one of: {', '.join(sorted(SUPPORTED_CHAINS))}"
            )
        return chain


class RiskFactor(BaseModel):
    type: str = Field(..., description="Category of risk, e.g. 'phishing', 'known_scam', 'format_anomaly'")
    description: str = Field(..., description="Human-readable explanation of this specific risk")


class AddressValidationResult(BaseAgentOutput):
    verdict: RiskVerdict = Field(..., description="Overall safety verdict: SAFE, FLAGGED, or UNKNOWN")
    detected_format: str = Field(..., description="Address format detected, e.g. 'ERC-20', 'EOA', 'Solana base58', 'invalid'")
    reasoning: str = Field(..., description="Step-by-step explanation of how the verdict was reached")
    risk_factors: list[RiskFactor] = Field(
        default_factory=list,
        description="List of individual risk factors identified. Empty if verdict is SAFE."
    )

    @model_validator(mode="after")
    def flagged_requires_risk_factors(self) -> "AddressValidationResult":
        if self.verdict == "FLAGGED" and not self.risk_factors:
            raise ValueError("verdict is FLAGGED but risk_factors is empty — LLM must explain why")
        return self


class RetrieveDocsArgs(BaseToolArgs):
    query: str = Field(..., description="Search query to look up in the address format knowledge base")
    chain: Optional[str] = Field(None, description="Optional chain filter to narrow results")


class AssessRiskArgs(BaseToolArgs):
    address: str = Field(..., description="The address to assess")
    chain: str = Field("unknown", description="The chain this address belongs to")
    context: Optional[str] = Field(None, description="Any additional context retrieved from docs")
