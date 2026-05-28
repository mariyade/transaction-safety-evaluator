import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL") or "gpt-4o-mini"
DEFAULT_N_RETRY: int = int(os.getenv("DEFAULT_N_RETRY") or "5")
