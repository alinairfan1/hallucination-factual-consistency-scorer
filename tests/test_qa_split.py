from scorer.benchmark.qa_split import split_question_answer


def test_splits_question_and_answer_scaffolding():
    raw = 'Question: "What is the capital of France?" Answer: Paris'
    question, answer = split_question_answer(raw)
    assert question == "What is the capital of France?"
    assert answer == "Paris"


def test_returns_raw_text_as_answer_when_no_scaffolding_present():
    question, answer = split_question_answer("A free-text live-scoring answer.")
    assert question == ""
    assert answer == "A free-text live-scoring answer."
