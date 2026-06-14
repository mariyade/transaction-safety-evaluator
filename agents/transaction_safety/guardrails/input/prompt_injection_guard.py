import re

from agents.transaction_safety.guardrails.base import GuardResult
from agents.transaction_safety.logger import get_logger

logger = get_logger(__name__)

# Phrases that signal an attempt to hijack the system prompt or override instructions.
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|your|the)\s+(instructions?|prompts?|rules?|guidelines?)",
    r"forget\s+(your|all|previous)\s+(instructions?|prompts?|rules?|context)",
    r"disregard\s+(your|all|previous)\s+(instructions?|rules?|guidelines?)",
    r"you\s+are\s+now\s+a\s+",
    r"act\s+as\s+(if\s+you\s+(are|were)|a\s+)",
    r"pretend\s+(to\s+be|you\s+are)",
    r"your\s+new\s+(instructions?|role|task)\s+(is|are)",
    r"override\s+(your|the)\s+(guidelines?|instructions?|rules?)",
    r"\bsystem\s*:\s*you\s+are\b",
    r"\bassistant\s*:\s*",
    r"</?(system|user|assistant|prompt)>",
    r"new\s+system\s+prompt",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"DAN\s+mode",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


class PromptInjectionGuard:
    """Detects prompt injection attempts in user-supplied text."""

    def check(self, text: str) -> GuardResult:
        for pattern in _COMPILED:
            if pattern.search(text):
                logger.warning("prompt injection pattern matched: %s", pattern.pattern[:60])
                return GuardResult(passed=False, error="Prompt injection detected in input")
        return GuardResult(passed=True)
