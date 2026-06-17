# Synthetic Golden Generation

These files are small manual utilities for generating candidate DeepEval `Golden` rows.
They are not pytest tests and should not run in CI by default.

Use them when you want to expand an evaluation dataset:

```bash
python tests/transaction_safety/evaluation/synthetic/from_docs.py
python tests/transaction_safety/evaluation/synthetic/from_contexts.py
python tests/transaction_safety/evaluation/synthetic/from_existing_goldens.py
```

Outputs are written to:

```txt
datasets/transaction_safety/synthetic/
```

Review generated rows before copying them into the real evaluation datasets.
