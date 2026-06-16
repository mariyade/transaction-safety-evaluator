# ruff: noqa: E402
import pytest

from tests.transaction_safety.evaluation.helpers import (
    agent_input_from_metadata,
    load_json_rows,
    retrieved_context,
    run_agent,
)

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

pytestmark = pytest.mark.evaluation


def _dataset(relative_path: str) -> EvaluationDataset:
    rows = load_json_rows(relative_path)
    return EvaluationDataset(goldens=[Golden(**row) for row in rows])


RAG_RETRIEVAL_DATASET = _dataset("datasets/transaction_safety/rag_retrieval_goldens.json")
RAG_GENERATION_DATASET = _dataset("datasets/transaction_safety/rag_generation_goldens.json")


@pytest.mark.parametrize("golden", RAG_RETRIEVAL_DATASET.goldens)
def test_rag_retrieval_metrics(golden):
    assert_test(
        LLMTestCase(
            input=golden.input,
            expected_output=golden.expected_output,
            retrieval_context=retrieved_context(golden.input),
        ),
        [
            ContextualRelevancyMetric(threshold=0.5),
            ContextualPrecisionMetric(threshold=0.5),
            ContextualRecallMetric(threshold=0.5),
        ],
    )


@pytest.mark.parametrize("golden", RAG_GENERATION_DATASET.goldens)
def test_rag_generation_metrics(agent, golden):
    result = run_agent(agent, agent_input_from_metadata(golden.additional_metadata))
    assert_test(
        LLMTestCase(
            input=golden.input,
            actual_output=result.reasoning,
            expected_output=golden.expected_output,
            retrieval_context=retrieved_context(golden.additional_metadata["context_query"]),
        ),
        [
            FaithfulnessMetric(threshold=0.5),
            AnswerRelevancyMetric(threshold=0.5),
        ],
    )
