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
│       └── pydantic_validator.py      ← validate_with_model, create_retry_prompt, validate_llm_response
│
├── agents/
│   └── transaction_safety/            ← reference implementation
│       ├── config.py                  ← MODEL, N_RETRY (overrides core defaults via .env)
│       ├── prompts.py                 ← SYSTEM_PROMPT, build_structured_output_prompt()
│       ├── tools.py                   ← TOOLS_SCHEMA, RISKY_PATTERNS, tool functions
│       ├── schemas.py                 ← AddressInput, AddressValidationResult, tool arg schemas
│       ├── knowledge_base.py          ← ChromaDB + LangChain RAG over data/docs/
│       └── agent.py                   ← TransactionSafetyAgent (clean class only)
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
| Guardrails | `tests/guardrails/` | Yes | Slow | Runtime safety checks: prompt injection on input, PII detection, hallucination on output |
| Evaluation | `tests/evaluation/` | Yes | Slow | DeepEval metrics: faithfulness (output grounded in retrieved docs), answer relevancy, G-Eval against golden verdicts |

**Rules:**
- Unit tests must never make network calls or import OpenAI
- Integration tests are auto-skipped if `OPENAI_API_KEY` is not set
- Guardrails and evaluation tests are marked and excluded from the default CI run until those layers are built
- All tests use real pytest files — no YAML, no custom DSL

### Commands

```bash
# unit only — no API key, runs in CI on every commit
pytest agents/transaction_safety/tests/unit/

# integration — requires OPENAI_API_KEY
pytest agents/transaction_safety/tests/integration/ -v

# unit + coverage report
pytest agents/transaction_safety/tests/unit/ --cov=agents/transaction_safety --cov-report=term-missing

# skip slow tests
pytest -m "not integration and not guardrails and not evaluation"

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

## TODO

- `test_knowledge_base.py` — retrieval-only tests using the RAG QA pairs from the original repo; query ChromaDB directly and assert reference keywords appear in retrieved chunks (no LLM required, fast and deterministic)
