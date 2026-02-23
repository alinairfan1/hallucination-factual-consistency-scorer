from pathlib import Path

from scorer.dataset import DatasetExample, load_examples

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_dataset.jsonl"


def test_load_examples_parses_all_lines():
    examples = load_examples(FIXTURE_PATH)
    assert len(examples) == 2
    assert all(isinstance(ex, DatasetExample) for ex in examples)


def test_load_examples_parses_fields_correctly():
    examples = load_examples(FIXTURE_PATH)
    first = examples[0]
    assert first.answer == "The Eiffel Tower is located in Paris and was completed in 1889."
    assert first.sources == [
        "The Eiffel Tower is a wrought-iron lattice tower in Paris, France.",
        "Construction of the Eiffel Tower finished in 1889.",
    ]
    assert first.label == "supported"
    assert examples[1].label == "hallucinated"


def test_load_examples_skips_blank_lines(tmp_path: Path):
    path = tmp_path / "with_blanks.jsonl"
    path.write_text(FIXTURE_PATH.read_text() + "\n\n")
    examples = load_examples(path)
    assert len(examples) == 2
