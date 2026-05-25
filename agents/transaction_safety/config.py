import os

from framework.core.config import DEFAULT_MODEL, DEFAULT_N_RETRY

MODEL: str | None = os.getenv("TRANSACTION_SAFETY_MODEL", DEFAULT_MODEL)
N_RETRY: int = int(os.getenv("TRANSACTION_SAFETY_N_RETRY", DEFAULT_N_RETRY))
