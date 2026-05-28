import pytest

from agents.transaction_safety.knowledge_base import retrieve

pytestmark = pytest.mark.evaluation

RAG_CASES = [
    (
        "ethereum address format 0x hexadecimal",
        ["0x", "40 hexadecimal", "42 characters"],
    ),
    (
        "solana address format base58 ed25519",
        ["Base58", "Ed25519", "32-44"],
    ),
    (
        "cross-chain transfer USDC permanent loss funds",
        ["PERMANENT LOSS", "bridge", "incompatible"],
    ),
    (
        "clipboard hijacking address verification copy paste",
        ["clipboard", "verify", "copy and paste"],
    ),
]


@pytest.mark.parametrize("query,expected_keywords", RAG_CASES)
def test_retrieval_contains_expected_keywords(query, expected_keywords):
    chunks = retrieve(query)
    combined = "\n".join(c["page_content"] for c in chunks).lower()
    missing = [kw for kw in expected_keywords if kw.lower() not in combined]
    assert not missing, f"Query '{query}' — missing keywords in retrieved chunks: {missing}"


def test_retrieval_returns_multiple_chunks():
    chunks = retrieve("blockchain address format")
    assert len(chunks) >= 2


def test_retrieval_has_non_empty_content():
    chunks = retrieve("ethereum")
    assert all("page_content" in c and len(c["page_content"]) > 10 for c in chunks)


def test_solana_query_does_not_return_only_ethereum():
    chunks = retrieve("solana base58 address")
    combined = "\n".join(c["page_content"] for c in chunks).lower()
    assert "solana" in combined, "Solana query should surface Solana content"
