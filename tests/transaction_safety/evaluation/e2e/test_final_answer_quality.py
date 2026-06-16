# ruff: noqa: E402
import pytest

from tests.transaction_safety.evaluation.helpers import retrieved_context, run_agent

deepeval = pytest.importorskip("deepeval")
deepeval_metrics = pytest.importorskip("deepeval.metrics")
deepeval_test_case = pytest.importorskip("deepeval.test_case")
assert_test = deepeval.assert_test
AnswerRelevancyMetric = deepeval_metrics.AnswerRelevancyMetric
FaithfulnessMetric = deepeval_metrics.FaithfulnessMetric
GEval = deepeval_metrics.GEval
HallucinationMetric = deepeval_metrics.HallucinationMetric
LLMTestCase = deepeval_test_case.LLMTestCase
SingleTurnParams = deepeval_test_case.SingleTurnParams

from agents.transaction_safety.pydantic_models import AddressInput, FreeTextInput

pytestmark = pytest.mark.evaluation


def test_faithfulness_ethereum_address(agent):
    result = run_agent(
        agent, AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="ethereum")
    )
    ctx = retrieved_context("ethereum address format 0x hexadecimal")
    tc = LLMTestCase(
        input="Evaluate this address: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 on ethereum",
        actual_output=result.reasoning if result else "",
        retrieval_context=ctx,
    )
    assert_test(tc, [FaithfulnessMetric(threshold=0.5)])


def test_hallucination_solana_on_ethereum(agent):
    result = run_agent(
        agent,
        AddressInput(address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", chain="ethereum"),
    )
    ctx = retrieved_context("solana address format ethereum mismatch")
    tc = LLMTestCase(
        input="Evaluate this address: 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM on ethereum",
        actual_output=result.reasoning if result else "",
        context=ctx,
    )
    assert_test(tc, [HallucinationMetric(threshold=0.5)])


def test_answer_relevancy_scam_detection(agent):
    text = "Someone sent me a link to claim free USDC by approving a contract. Should I do it?"
    result = run_agent(agent, FreeTextInput(text=text))
    tc = LLMTestCase(
        input=text,
        actual_output=result.reasoning if result else "",
    )
    assert_test(tc, [AnswerRelevancyMetric(threshold=0.5)])


def test_format_chain_consistency(agent):
    result = run_agent(
        agent,
        AddressInput(address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", chain="ethereum"),
    )
    ctx = retrieved_context("solana address format ethereum compatibility")
    tc = LLMTestCase(
        input="Evaluate this address: 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM on ethereum",
        actual_output=result.reasoning if result else "",
        retrieval_context=ctx,
    )
    assert_test(
        tc,
        [
            GEval(
                name="Format-Chain Consistency",
                evaluation_steps=[
                    "Check if the reasoning identifies the address as Solana format (Base58, not starting with 0x)",
                    "Check if the reasoning explains why a Solana address is incompatible with Ethereum",
                    "Check that the verdict reflects this format-chain mismatch as a risk",
                ],
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                    SingleTurnParams.RETRIEVAL_CONTEXT,
                ],
                threshold=0.5,
            )
        ],
    )
