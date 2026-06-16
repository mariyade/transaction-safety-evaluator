from dataclasses import dataclass


@dataclass
class GuardResult:
    passed: bool
    error: str | None = None
