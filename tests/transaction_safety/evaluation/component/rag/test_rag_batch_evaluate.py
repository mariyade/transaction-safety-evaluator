# ruff: noqa: E402
import pytest

from tests.transaction_safety.evaluation.helpers import load_json_rows, retrieved_context

deepeval = pytest.importorskip("deepeval")
deepeval_evaluate = pytest.importorskip("deepeval.evaluate")
deepeval_metrics = pytest.importorskip("deepeval.metrics")
deepeval_test_case = pytest.importorskip("deepeval.test_case")

evaluate = deepeval.evaluate
CacheConfig = deepeval_evaluate.CacheConfig
DisplayConfig = deepeval_evaluate.DisplayConfig
ErrorConfig = deepeval_evaluate.ErrorConfig
ContextualPrecisionMetric = deepeval_metrics.ContextualPrecisionMetric
ContextualRecallMetric = deepeval_metrics.ContextualRecallMetric
ContextualRelevancyMetric = deepeval_metrics.ContextualRelevancyMetric
LLMTestCase = deepeval_test_case.LLMTestCase

pytestmark = pytest.mark.evaluation


def test_rag_retrieval_batch_evaluate_with_cache():
    rows = load_json_rows("datasets/transaction_safety/rag_retrieval_goldens.json")
    test_cases = [
        LLMTestCase(
            input=row["input"],
            expected_output=row["expected_output"],
            retrieval_context=retrieved_context(row["input"]),
        )
        for row in rows
    ]

    result = evaluate(
        test_cases=test_cases,
        metrics=[
            ContextualRelevancyMetric(threshold=0.5),
            ContextualPrecisionMetric(threshold=0.5),
            ContextualRecallMetric(threshold=0.5),
        ],
        cache_config=CacheConfig(write_cache=True, use_cache=True),
        error_config=ErrorConfig(ignore_errors=False),
        display_config=DisplayConfig(
            print_results=True,
            results_folder="evaluation_results/deepeval",
        ),
    )

    failed = [test for test in result.test_results if not test.success]
    assert not failed, [test.name or test.input for test in failed]
