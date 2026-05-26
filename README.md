# AI Evaluation Framework

A customisable evaluation framework for AI agents and RAG pipelines.
Uses Pydantic for structured output validation, Guardrails for safety checks, and GitHub Actions for CI.

The `transaction_safety` agent is the reference implementation.

---

## Project structure

```
ai_evaluation_framework/
│
├── framework/
│   └── core/                          ← shared base, never agent-specific
│       ├── config.py                  ← OPENAI_API_KEY, DEFAULT_MODEL, DEFAULT_N_RETRY
│       ├── schemas.py                 ← BaseAgentInput, BaseAgentOutput, BaseToolArgs
│       ├── base_agent.py              ← abstract BaseAgent (model + system_prompt + run)
│       ├── pydantic_validator.py      ← validate_with_model, create_retry_prompt, validate_llm_response
│       └── guardrails/
│           ├── base.py                ← GuardResult dataclass (passed, error)
│           └── pii_guard.py          ← PIIGuard — Presidio-based, reusable by any agent
│
├── agents/
│   └── transaction_safety/            ← reference implementation
│       ├── config.py                  ← MODEL, N_RETRY (overrides core defaults via .env)
│       ├── prompts.py                 ← SYSTEM_PROMPT, build_structured_output_prompt()
│       ├── tools.py                   ← TOOLS_SCHEMA, RISKY_PATTERNS, tool functions
│       ├── schemas.py                 ← AddressInput, AddressValidationResult, tool arg schemas
│       ├── knowledge_base.py          ← ChromaDB + LangChain RAG over data/docs/
│       ├── agent.py                   ← TransactionSafetyAgent (clean class only)
│       └── guardrails/
│           ├── crypto_secrets_guard.py  ← regex: private keys, seed phrases
│           ├── prompt_injection_guard.py← keyword: prompt hijacking attempts
│           └── verdict_guard.py        ← output: FLAGGED must have risk factors, confidence floor
│
├── data/
│   └── docs/                          ← knowledge base (address_formats.txt etc.)
│
├── .env.example                       ← copy to .env and fill in your keys
└── requirements.txt
```

---

## Setup

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in OPENAI_API_KEY
```

---

## Configuration

All configuration is in `.env`. The framework reads it automatically via `python-dotenv`.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required |
| `DEFAULT_MODEL` | `gpt-4o-mini` | Model used by all agents unless overridden |
| `DEFAULT_N_RETRY` | `5` | Retry attempts for Pydantic validation failures |
| `TRANSACTION_SAFETY_MODEL` | `DEFAULT_MODEL` | Override model for this agent only |
| `TRANSACTION_SAFETY_N_RETRY` | `DEFAULT_N_RETRY` | Override retries for this agent only |

You can also override the model at instantiation without touching `.env`:

```python
agent = TransactionSafetyAgent()                  # uses .env or default
agent = TransactionSafetyAgent(model="gpt-4o")    # override at runtime
```

---

## How to add a new agent

Copy `agents/transaction_safety/` as a starting point and replace the contents:

```
agents/
  your_agent_name/
    __init__.py
    config.py          ← set MODEL + N_RETRY, add agent-specific env vars
    prompts.py         ← write SYSTEM_PROMPT + build_structured_output_prompt()
    tools.py           ← define TOOLS_SCHEMA + tool functions
    schemas.py         ← define YourInput, YourOutput, tool arg schemas
    knowledge_base.py  ← set up RAG if needed (or delete if not)
    agent.py           ← implement YourAgent(BaseAgent)
    tests/
      __init__.py
      unit/         ← test_schemas.py, test_tools.py, test_pydantic_validator.py
      integration/  ← test_agent.py
      guardrails/   ← test_guardrails_input.py, test_guardrails_output.py
      evaluation/   ← test_deepeval.py
```

Every agent must implement four things:

| What | Why |
|---|---|
| `system_prompt` property | defines the agent's role and behaviour |
| `tools_schema` property | list of OpenAI function definitions for this agent |
| `_handle_tool_call(tool_call)` | routes tool calls to your tool functions |
| `run(input)` | formats input into a user message, calls `_run_tool_loop()`, returns structured output |

`_call_llm` and `_run_tool_loop` are provided by `BaseAgent` — no need to implement them.

### Implementation sequence

Follow this order for every new agent:

1. **`schemas.py`** — define input/output/tool arg models; add `field_validator` and `model_validator` for all constraints
2. **`config.py`** — set `MODEL` and `N_RETRY`; add any agent-specific env vars
3. **`prompts.py`** — write `SYSTEM_PROMPT` and `build_structured_output_prompt()`
4. **`tools.py`** — define `TOOLS_SCHEMA` and tool functions; `handle_tool_call` validates args via Pydantic
5. **`knowledge_base.py`** — set up ChromaDB + LangChain RAG over `data/docs/`; delete if no RAG needed
6. **`agent.py`** — implement `YourAgent(BaseAgent)`; wire tool loop and `validate_llm_response`
7. **`tests/`** — unit tests for schemas and validator; integration tests for the agent (requires API key)
8. **Guardrails** — add input guards (prompt injection, PII) and output guards (hallucination, grounding)
9. **GitHub Actions** — CI workflow that runs tests on every PR
10. **Phoenix tracing** — add last, once everything else is stable

---

## Running the agent

```bash
source venv/bin/activate
python -m run
```

---

## Test strategy

Tests are split into four layers. Each layer has a distinct scope, cost, and API requirement.

| Layer | Folder | API key | Speed | What it covers |
|---|---|---|---|---|
| Unit | `tests/unit/` | No | Fast | Pydantic schema validation, retry logic, tool routing, prompt building — pure functions only |
| Integration | `tests/integration/` | Yes | Slow | Full agent runs against real OpenAI API; asserts correct verdict and confidence for known inputs |
| Guardrails | `tests/guardrails/` | No | Fast | Guard logic: prompt injection patterns, regex private keys/seed phrases, output verdict rules |
| Evaluation | `tests/evaluation/` | Yes | Slow | Code-based evals (F1, ROC-AUC) + LLM-judge evals via DeepEval (faithfulness, relevancy, G-Eval) |

**Rules:**
- Unit tests must never make network calls or import OpenAI
- Integration tests are auto-skipped if `OPENAI_API_KEY` is not set
- Guardrails and evaluation tests are marked and excluded from the default CI run until those layers are built
- All tests use real pytest files — no YAML, no custom DSL

### Commands

```bash
# unit only — no API key, runs in CI on every commit
pytest agents/transaction_safety/tests/unit/

# guardrails — no API key, tests guard logic directly
pytest agents/transaction_safety/tests/guardrails/

# integration — requires OPENAI_API_KEY
pytest agents/transaction_safety/tests/integration/ -v

# unit + guardrails + coverage report
pytest agents/transaction_safety/tests/unit/ agents/transaction_safety/tests/guardrails/ \
  --cov=agents/transaction_safety --cov-report=term-missing

# skip slow/API tests
pytest -m "not integration and not evaluation"

# run a specific layer
pytest -m integration
pytest -m guardrails
pytest -m evaluation
```

---

## What the core provides (never modify for a specific agent)

| File | What it gives you |
|---|---|
| `framework/core/config.py` | `OPENAI_API_KEY`, `DEFAULT_MODEL`, `DEFAULT_N_RETRY` |
| `framework/core/schemas.py` | `BaseAgentInput` (+ `request_id`, `timestamp`), `FreeTextInput` (+ `text`), `BaseAgentOutput` (+ `verdict`, `confidence`), `BaseToolArgs` |
| `framework/core/base_agent.py` | `BaseAgent` — shared OpenAI client, `_call_llm()`, `_run_tool_loop()`; agents implement `system_prompt`, `tools_schema`, `_handle_tool_call()`, `run()` |
| `framework/core/pydantic_validator.py` | `validate_with_model()`, `create_retry_prompt()`, `validate_llm_response()` |
| `framework/core/logger.py` | `get_logger(__name__)` — call in any module to get a named, pre-configured logger |

Logs are written to both stdout and a file. Default file path is `logs/agent.log` (created automatically, excluded from git).

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `LOG_DIR` | `logs/` | directory for log files; each run creates `agent_YYYYMMDD_HHMMSS.log` |

Set `LOG_LEVEL=DEBUG` to see full LLM prompts and responses.

---

## Guardrails

Guardrails run before and after the LLM — the agent returns `(None, error_message)` if any guard fires. No exception is raised; the caller decides what to do.

### Input guards (run before the LLM call)

| Guard | Location | What it catches |
|---|---|---|
| `PromptInjectionGuard` | `agents/transaction_safety/guardrails/` | "ignore instructions", "you are now", `<system>` tags, jailbreak patterns |
| `PIIGuard` | `framework/core/guardrails/` | Names, emails, phones, SSN, IBAN — uses Microsoft Presidio. Reusable by any agent. |
| `CryptoSecretsGuard` | `agents/transaction_safety/guardrails/` | Ethereum/WIF/Solana private keys (regex), BIP-39 seed phrases (12/15/18/21/24 consecutive words) |

### Output guard (runs after structured output is validated)

| Guard | Location | What it checks |
|---|---|---|
| `VerdictGuard` | `agents/transaction_safety/guardrails/` | FLAGGED must have ≥1 risk factor with non-trivial description; FLAGGED confidence must be ≥ 0.4 |

### Setup

Presidio requires a spaCy language model. Run once after `pip install`:

```bash
python -m spacy download en_core_web_lg
```

### How to add guards to a new agent

1. Create `agents/your_agent/guardrails/` with domain-specific guards
2. Reuse `PIIGuard` from `framework/core/guardrails/` for general PII
3. In your agent's `__init__`, set `self._input_guards = [...]` and `self._output_guard = ...`
4. In `run()`, call each input guard before the LLM and the output guard after

Every guard has one method: `check(text_or_result) -> GuardResult(passed, error)`.

---

## Evaluation

The evaluation layer measures agent quality against a golden set of known inputs and expected outputs. It runs offline — not on every request — typically before releasing a new prompt, model, or RAG update.

### Two types of evals

**Code-based evals** — deterministic, no API calls, fast. Computed by comparing predicted vs. expected verdicts across the golden set.

| Metric | What it measures |
|---|---|
| Accuracy | % of verdicts correct overall |
| Precision | Of all FLAGGED predictions, how many were actually risky |
| Recall | Of all actually risky inputs, how many were caught |
| F1 | Harmonic mean of precision and recall — the primary metric |
| ROC-AUC | Quality of `confidence` as a probability score across all thresholds |
| Confusion matrix | Full breakdown of SAFE/FLAGGED/UNKNOWN predictions vs. actuals |
| Retry rate | % of runs that needed a Pydantic validation retry |
| Guard trigger rate | % of inputs blocked by each guard |
| Latency | p50/p95 run time |

Recall matters more than precision here — a missed scam (false negative) is worse than a false alarm (false positive). F1 is the headline number; use recall to set the floor.

**LLM-judge evals** — uses a second LLM (GPT-4) to score outputs. Slower and costs money. Run these when validating a major prompt or model change, not on every commit.

| Metric | Tool | What it measures |
|---|---|---|
| Faithfulness | DeepEval | Is the reasoning grounded in the retrieved docs, or did the LLM hallucinate blockchain facts? |
| Answer relevancy | DeepEval | Is the output actually about the question asked? |
| Contextual precision | DeepEval | Are the retrieved RAG chunks relevant to the query? |
| Contextual recall | DeepEval | Did retrieval surface all the relevant chunks? |
| G-Eval (custom) | DeepEval | Your own criteria in plain English, scored by an LLM judge |

G-Eval example for this agent:
```python
GEval(
    name="Format-Chain Consistency",
    criteria="Does the verdict correctly identify a mismatch between address format and the specified chain?",
    evaluation_steps=[
        "Check if detected_format is consistent with the chain field",
        "Check that FLAGGED verdicts explain the format mismatch clearly",
    ],
)
```

### Golden set

Both eval types require a golden set: a list of inputs with expected verdicts. The integration tests (`tests/integration/test_agent.py`) are the starting point — same cases, same expected verdicts, but the evaluation layer collects scores across all of them rather than just asserting pass/fail.

---

## TODO

- `test_knowledge_base.py` — retrieval-only tests using the RAG QA pairs from the original repo; query ChromaDB directly and assert reference keywords appear in retrieved chunks (no LLM required, fast and deterministic)
