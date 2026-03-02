from scripts.prepare_halueval_subset import convert_halueval_rows


def test_convert_halueval_rows_produces_two_examples_per_row():
    raw_rows = [
        {
            "knowledge": "Paris is the capital of France.",
            "question": "What is the capital of France?",
            "right_answer": "Paris is the capital of France.",
            "hallucinated_answer": "Berlin is the capital of France.",
        }
    ]

    examples = convert_halueval_rows(raw_rows, limit=10)

    assert len(examples) == 2
    assert examples[0] == {
        "answer": 'Question: "What is the capital of France?" '
        "Answer: Paris is the capital of France.",
        "sources": ["Paris is the capital of France."],
        "label": "supported",
    }
    assert examples[1] == {
        "answer": 'Question: "What is the capital of France?" '
        "Answer: Berlin is the capital of France.",
        "sources": ["Paris is the capital of France."],
        "label": "hallucinated",
    }


def test_convert_halueval_rows_respects_limit():
    raw_rows = [
        {"knowledge": "k1", "question": "q1", "right_answer": "r1", "hallucinated_answer": "h1"},
        {"knowledge": "k2", "question": "q2", "right_answer": "r2", "hallucinated_answer": "h2"},
        {"knowledge": "k3", "question": "q3", "right_answer": "r3", "hallucinated_answer": "h3"},
    ]

    examples = convert_halueval_rows(raw_rows, limit=2)

    assert len(examples) == 4  # 2 rows * 2 examples each


def test_convert_halueval_rows_handles_empty_input():
    assert convert_halueval_rows([], limit=50) == []
