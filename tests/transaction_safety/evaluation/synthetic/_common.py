from __future__ import annotations

import json
from pathlib import Path

from deepeval.dataset import Golden
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import StylingConfig

PROJECT_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_DIR = PROJECT_ROOT / "datasets" / "transaction_safety" / "synthetic"


def repo_path(relative_path: str) -> str:
    return str(PROJECT_ROOT / relative_path)


def transaction_safety_synthesizer() -> Synthesizer:
    return Synthesizer(
        styling_config=StylingConfig(
            scenario="Users checking blockchain addresses, wallet approvals, and crypto safety questions.",
            task="Generate transaction-safety evaluation questions with expected safety-focused answers.",
            input_format="A concise blockchain safety question or address-evaluation request.",
            expected_output_format="A concise expected answer or verdict explanation grounded in the provided context.",
        )
    )


def save_goldens(goldens: list[Golden], filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    payload = [golden.model_dump(exclude_none=True) for golden in goldens]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(goldens)} goldens to {path}")


def load_goldens(relative_path: str) -> list[Golden]:
    rows = json.loads(Path(repo_path(relative_path)).read_text(encoding="utf-8"))
    return [Golden(**row) for row in rows]
