from _common import repo_path, save_goldens, transaction_safety_synthesizer


def main() -> None:
    synthesizer = transaction_safety_synthesizer()
    goldens = synthesizer.generate_goldens_from_docs(
        document_paths=[repo_path("data/docs/address_formats.txt")],
        include_expected_output=True,
        max_goldens_per_context=2,
    )
    save_goldens(goldens, "from_docs.json")


if __name__ == "__main__":
    main()
