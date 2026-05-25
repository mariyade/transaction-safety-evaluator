import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL: str | None = os.getenv("DEFAULT_MODEL")
DEFAULT_N_RETRY: int = int(os.getenv("DEFAULT_N_RETRY", "5"))
