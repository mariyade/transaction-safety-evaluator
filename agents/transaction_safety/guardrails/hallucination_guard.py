import re
from typing import Callable, Optional

from framework.core.guardrails.base import GuardResult
from framework.core.logger import get_logger

logger = get_logger(__name__)

_MIN_CLAIM_LENGTH = 25


def _split_into_claims(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if len(s) >= _MIN_CLAIM_LENGTH]


class HallucinationGuard:
    """Checks output reasoning against context using NLI.

    Each claim is checked against each context chunk separately so the NLI
    model receives short, focused premise-hypothesis pairs rather than one
    long concatenated string. This avoids truncation artifacts and topic-
    mismatch false positives.

    Flags claims that directly CONTRADICT a context chunk. NEUTRAL claims are
    allowed — the agent may draw on general knowledge alongside retrieved docs.

    nli_fn is injectable so tests can run without downloading the model:
        HallucinationGuard(nli_fn=lambda ctx, claim: {"entailment": 0.9, ...})
    """

    def __init__(
        self,
        contradiction_threshold: float = 0.85,
        nli_fn: Optional[Callable[[str, str], dict[str, float]]] = None,
    ):
        self._threshold = contradiction_threshold
        self._nli_fn = nli_fn or self._load_nli()

    @staticmethod
    def _load_nli() -> Callable[[str, str], dict[str, float]]:
        from transformers import pipeline

        pipe = pipeline(
            "text-classification",
            model="cross-encoder/nli-deberta-v3-small",
            top_k=None,
            device=-1,
        )

        def _predict(context: str, claim: str) -> dict[str, float]:
            results = pipe({"text": context, "text_pair": claim})
            return {r["label"].lower(): r["score"] for r in results}

        return _predict

    def check(self, reasoning: str, context: str) -> GuardResult:
        """Check reasoning against context.

        context may be a single string or newline-separated chunks.
        Each chunk is checked independently to keep NLI inputs short.
        """
        chunks = [c.strip() for c in context.split("\n\n") if c.strip()]
        if not chunks:
            return GuardResult(passed=True)

        claims = _split_into_claims(reasoning)
        if not claims:
            return GuardResult(passed=True)

        for chunk in chunks:
            for claim in claims:
                scores = self._nli_fn(chunk, claim)
                contradiction_score = scores.get("contradiction", 0.0)

                if contradiction_score >= self._threshold:
                    logger.warning(
                        "hallucination detected — contradiction score=%.2f: '%s'",
                        contradiction_score,
                        claim[:100],
                    )
                    return GuardResult(
                        passed=False,
                        error=(
                            f"Output contradicts retrieved context "
                            f"(score={contradiction_score:.2f}): '{claim[:80]}'"
                        ),
                    )

        return GuardResult(passed=True)
