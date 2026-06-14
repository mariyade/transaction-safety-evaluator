import json
from pathlib import Path

import pytest

deepeval = pytest.importorskip("deepeval")
deepeval_dataset = pytest.importorskip("deepeval.dataset")
deepeval_metrics = pytest.importorskip("deepeval.metrics")
deepeval_test_case = pytest.importorskip("deepeval.test_case")
assert_test = deepeval.assert_test
AnswerRelevancyMetric = deepeval_metrics.AnswerRelevancyMetric
ContextualPrecisionMetric = deepeval_metrics.ContextualPrecisionMetric
ContextualRecallMetric = deepeval_metrics.ContextualRecallMetric
ContextualRelevancyMetric = deepeval_metrics.ContextualRelevancyMetric
FaithfulnessMetric = deepeval_metrics.FaithfulnessMetric
EvaluationDataset = deepeval_dataset.EvaluationDataset
Golden = deepeval_dataset.Golden
LLMTestCase = deepeval_test_case.LLMTestCase

from agents.transaction_safety.knowledge_base import retrieve
from agents.transaction_safety.schemas import AddressInput, FreeTextInput

pytestmark = pytest.mark.evaluation


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "datasets/transaction_safety").exists():
            return parent
    raise RuntimeError("Could not find repository root from RAG eval test path")


REPO_ROOT = _repo_root()


def _load_goldens(path: Path) -> EvaluationDataset:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return EvaluationDataset(goldens=[Golden(**row) for row in rows])


RAG_RETRIEVAL_DATASET = _load_goldens(REPO_ROOT / "datasets/transaction_safety/rag_retrieval_goldens.json")
RAG_GENERATION_DATASET = _load_goldens(REPO_ROOT / "datasets/transaction_safety/rag_generation_goldens.json")


def _context(query: str) -> list[str]:
    return [chunk["page_content"] for chunk in retrieve(query)]


def _test_case(golden: Golden) -> LLMTestCase:
    return LLMTestCase(
        input=golden.input,
        expected_output=golden.expected_output,
        retrieval_context=_context(golden.input),
    )


def _run(agent, inp):
    result, error = agent.run(inp)
    assert error is None
    assert result is not None
    return result


def _agent_input_from_metadata(metadata: dict):
    if metadata["input_type"] == "address":
        return AddressInput(**metadata["agent_input"])
    if metadata["input_type"] == "free_text":
        return FreeTextInput(**metadata["agent_input"])
    raise ValueError(f"Unsupported input_type: {metadata['input_type']}")


def _generation_test_case(agent, golden: Golden) -> LLMTestCase:
    result = _run(agent, _agent_input_from_metadata(golden.additional_metadata))
    return LLMTestCase(
        input=golden.input,
        actual_output=result.reasoning,
        expected_output=golden.expected_output,
        retrieval_context=_context(golden.additional_metadata["context_query"]),
    )


@pytest.mark.parametrize("golden", RAG_RETRIEVAL_DATASET.goldens)
def test_rag_retrieval_metrics(golden):
    assert_test(_test_case(golden), [
        ContextualRelevancyMetric(threshold=0.5),
        ContextualPrecisionMetric(threshold=0.5),
        ContextualRecallMetric(threshold=0.5),
    ])


@pytest.mark.parametrize("golden", RAG_GENERATION_DATASET.goldens)
def test_rag_generation_metrics(agent, golden):
    assert_test(_generation_test_case(agent, golden), [
        FaithfulnessMetric(threshold=0.5),
        AnswerRelevancyMetric(threshold=0.5),
    ])
