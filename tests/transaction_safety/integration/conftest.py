import os

import pytest


def pytest_collection_modifyitems(items):
    if not os.getenv("OPENAI_API_KEY"):
        skip = pytest.mark.skip(reason="OPENAI_API_KEY not set")
        for item in items:
            if "integration" in str(item.fspath):
                item.add_marker(skip)
