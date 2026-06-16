import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
MODEL: str = os.getenv("TRANSACTION_SAFETY_MODEL") or os.getenv("DEFAULT_MODEL") or "gpt-4o-mini"
N_RETRY: int = int(os.getenv("TRANSACTION_SAFETY_N_RETRY") or os.getenv("DEFAULT_N_RETRY") or "5")
TEMPERATURE: float = float(
    os.getenv("TRANSACTION_SAFETY_TEMPERATURE") or os.getenv("DEFAULT_TEMPERATURE") or "0"
)
