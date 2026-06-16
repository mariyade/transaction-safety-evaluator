from agents.transaction_safety.guardrails.base import GuardResult
from agents.transaction_safety.logger import get_logger

logger = get_logger(__name__)

# Presidio entity types that are relevant for most agents.
# Extend or override in subclasses for domain-specific PII.
DEFAULT_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
]


class PIIGuard:
    """Detects general PII using Microsoft Presidio"""

    def __init__(
        self,
        entities: list[str] | None = None,
        score_threshold: float = 0.5,
    ):
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()
        self._entities = entities or DEFAULT_ENTITIES
        self._score_threshold = score_threshold

    def _analyze(self, text: str):
        return self._analyzer.analyze(
            text=text,
            language="en",
            entities=self._entities,
            score_threshold=self._score_threshold,
        )

    def check(self, text: str) -> GuardResult:
        results = self._analyze(text)
        if results:
            found = sorted({r.entity_type for r in results})
            logger.warning("PII detected in input: %s", found)
            return GuardResult(passed=False, error=f"PII detected: {', '.join(found)}")
        return GuardResult(passed=True)

    def anonymize(self, text: str) -> str:
        """Replace detected PII with type placeholders, e.g. <PERSON>."""
        results = self._analyze(text)
        if not results:
            return text
        return self._anonymizer.anonymize(text=text, analyzer_results=results).text
