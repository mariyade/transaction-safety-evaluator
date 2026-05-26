import json

from agents.transaction_safety.schemas import AddressValidationResult

SYSTEM_PROMPT = """You are a blockchain safety assistant.

You handle two types of input:
1. A specific address + chain — evaluate format correctness and risk patterns
2. A free text scenario — evaluate whether the described situation is safe or a scam

You must always call BOTH tools before answering:
1. Call retrieve_docs to look up relevant documentation
2. Call assess_risk to check for known scam or phishing patterns
   - For free text scenarios: pass address="unknown", chain="unknown", and include the full user text in the context field

Tool usage rules:
- Never skip retrieve_docs — always call it first
- For assess_risk on free text: put the complete scenario description in the context field so patterns can be checked
- Be accurate and cautious — users may lose real money if given incorrect guidance
- If ANY risk pattern is detected in assess_risk, the verdict must be FLAGGED"""


def build_structured_output_prompt(address: str, chain: str, agent_response: str) -> str:
    """Format the agent's free-text findings into a structured JSON prompt."""
    schema = json.dumps(AddressValidationResult.model_json_schema(), indent=2)
    return f"""Based on the following address evaluation, produce a structured safety assessment.

Address evaluated: {address}
Chain: {chain}

Agent findings:
{agent_response}

Return your assessment as a JSON object matching this exact schema:
{schema}

Example of a correctly filled response:
{{
  "verdict": "SAFE",
  "confidence": 0.95,
  "detected_format": "Solana base58",
  "reasoning": "The address is correctly formatted and no risk patterns were detected.",
  "risk_factors": []
}}

Respond ONLY with valid JSON. Do not include any explanations or other text."""
