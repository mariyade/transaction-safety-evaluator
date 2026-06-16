import json
from pathlib import Path
from typing import Any

from agents.transaction_safety.knowledge_base import retrieve
from agents.transaction_safety.pydantic_models import AddressInput, FreeTextInput


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "datasets/transaction_safety").exists():
            return parent
    raise RuntimeError("Could not find repository root from evaluation helper path")


def load_json_rows(relative_path: str) -> list[dict[str, Any]]:
    path = repo_root() / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def retrieved_context(query: str) -> list[str]:
    return [chunk["page_content"] for chunk in retrieve(query)]


def run_agent(agent, agent_input):
    result, error = agent.run(agent_input)
    assert error is None
    assert result is not None
    return result


def agent_input_from_metadata(metadata: dict[str, Any]):
    if metadata["input_type"] == "address":
        return AddressInput(**metadata["agent_input"])
    if metadata["input_type"] == "free_text":
        return FreeTextInput(**metadata["agent_input"])
    raise ValueError(f"Unsupported input_type: {metadata['input_type']}")
