import os

from framework.core.config import DEFAULT_MODEL, DEFAULT_N_RETRY

MODEL: str = os.getenv("TRANSACTION_SAFETY_MODEL") or DEFAULT_MODEL
N_RETRY: int = int(os.getenv("TRANSACTION_SAFETY_N_RETRY") or DEFAULT_N_RETRY)
