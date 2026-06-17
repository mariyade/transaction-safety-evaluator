from _common import load_goldens, save_goldens, transaction_safety_synthesizer


def main() -> None:
    synthesizer = transaction_safety_synthesizer()
    seed_goldens = load_goldens("datasets/transaction_safety/rag_generation_goldens.json")
    goldens = synthesizer.generate_goldens_from_goldens(
        goldens=seed_goldens,
        max_goldens_per_golden=2,
    )
    save_goldens(goldens, "from_existing_goldens.json")


if __name__ == "__main__":
    main()
