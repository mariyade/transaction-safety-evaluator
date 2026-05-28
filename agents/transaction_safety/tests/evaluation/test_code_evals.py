import pytest

sklearn_metrics = pytest.importorskip("sklearn.metrics")
accuracy_score = sklearn_metrics.accuracy_score
f1_score = sklearn_metrics.f1_score
recall_score = sklearn_metrics.recall_score
roc_auc_score = sklearn_metrics.roc_auc_score

from agents.transaction_safety.schemas import AddressInput
from framework.core.schemas import FreeTextInput

pytestmark = pytest.mark.evaluation

# Ground truth: inputs paired with expected verdicts.
# Recall matters more than precision — a missed scam is worse than a false alarm.
GOLDEN_SET = [
    (AddressInput(address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain="ethereum"), "SAFE"),
    (AddressInput(address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", chain="solana"), "SAFE"),
    (AddressInput(address="0xdAC17F958D2ee523a2206206994597C13D831ec7", chain="polygon"), "SAFE"),
    (FreeTextInput(text="Is 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 a valid Ethereum USDC contract?"), "SAFE"),
    (AddressInput(address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", chain="ethereum"), "FLAGGED"),
    (FreeTextInput(text="Someone sent me a link to claim free USDC by approving a contract. Should I do it?"), "FLAGGED"),
    (FreeTextInput(text="A DeFi site wants unlimited USDC approval for 500% APY — is this safe?"), "FLAGGED"),
    (FreeTextInput(text="Send 0.1 ETH first and I'll send you 0.5 ETH back — guaranteed return"), "FLAGGED"),
]


@pytest.fixture(scope="module")
def eval_results(agent):
    results = []
    for inp, expected in GOLDEN_SET:
        result, error = agent.run(inp)
        results.append({
            "expected": expected,
            "predicted": result.verdict if result else "ERROR",
            "confidence": result.confidence if result else 0.0,
        })
    return results


def _binary(results):
    """Convert to binary labels. FLAGGED=1, SAFE=0. Skips non-binary predictions."""
    y_true, y_score = [], []
    for r in results:
        if r["expected"] not in ("SAFE", "FLAGGED"):
            continue
        if r["predicted"] not in ("SAFE", "FLAGGED"):
            continue
        y_true.append(1 if r["expected"] == "FLAGGED" else 0)
        y_score.append(r["confidence"] if r["predicted"] == "FLAGGED" else 1 - r["confidence"])
    return y_true, y_score


def test_accuracy(eval_results):
    y_true, y_score = _binary(eval_results)
    y_pred = [1 if s >= 0.5 else 0 for s in y_score]
    acc = accuracy_score(y_true, y_pred)
    print(f"\nAccuracy: {acc:.2f}")
    assert acc >= 0.75


def test_recall_floor(eval_results):
    y_true, y_score = _binary(eval_results)
    y_pred = [1 if s >= 0.5 else 0 for s in y_score]
    rec = recall_score(y_true, y_pred)
    print(f"\nRecall: {rec:.2f}")
    assert rec >= 0.75


def test_f1_floor(eval_results):
    y_true, y_score = _binary(eval_results)
    y_pred = [1 if s >= 0.5 else 0 for s in y_score]
    f1 = f1_score(y_true, y_pred)
    print(f"\nF1: {f1:.2f}")
    assert f1 >= 0.75


def test_roc_auc(eval_results):
    y_true, y_score = _binary(eval_results)
    auc = roc_auc_score(y_true, y_score)
    print(f"\nROC-AUC: {auc:.2f}")
    assert auc >= 0.75


def test_no_high_confidence_missed_scams(eval_results):
    """A FLAGGED case predicted SAFE with high confidence is a critical failure."""
    for r in eval_results:
        if r["expected"] == "FLAGGED" and r["predicted"] == "SAFE":
            assert r["confidence"] < 0.8, (
                f"Critical: FLAGGED case predicted SAFE with confidence {r['confidence']}"
            )
