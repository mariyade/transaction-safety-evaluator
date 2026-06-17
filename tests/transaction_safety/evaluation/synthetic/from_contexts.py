from _common import save_goldens, transaction_safety_synthesizer

CONTEXTS = [
    [
        "Ethereum addresses use 0x followed by 40 hexadecimal characters. "
        "EVM-compatible chains such as Base, Polygon, Arbitrum, and Optimism share this format."
    ],
    [
        "Solana addresses are Base58-encoded Ed25519 public keys. They do not start with 0x, "
        "and direct ERC-20 transfers to Solana addresses can result in permanent loss."
    ],
    [
        "Cross-chain transfers require a supported bridge. Sending ERC-20 USDC directly to a "
        "Solana address, or SPL USDC directly to an Ethereum address, can permanently lose funds."
    ],
]


def main() -> None:
    synthesizer = transaction_safety_synthesizer()
    goldens = synthesizer.generate_goldens_from_contexts(
        contexts=CONTEXTS,
        max_goldens_per_context=2,
    )
    save_goldens(goldens, "from_contexts.json")


if __name__ == "__main__":
    main()
