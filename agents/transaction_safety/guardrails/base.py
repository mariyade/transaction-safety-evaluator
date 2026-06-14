from dataclasses import dataclass
from typing import Optional


@dataclass
class GuardResult:
    passed: bool
    error: Optional[str] = None
