from scorer.aggregation import aggregate
from scorer.schemas import FlaggedClaim


def test_aggregate_empty_list_returns_vacuous_full_score():
    score, flagged = aggregate([])

    assert score == 1.0
    assert flagged == []


def test_aggregate_all_entailed_returns_score_one_and_no_flags():
    claim_verdicts = [
        ("claim one", "entailed", "supported by source"),
        ("claim two", "entailed", "supported by source"),
    ]

    score, flagged = aggregate(claim_verdicts)

    assert score == 1.0
    assert flagged == []


def test_aggregate_mixed_verdicts_computes_fraction_and_flags_non_entailed():
    claim_verdicts = [
        ("claim one", "entailed", "supported"),
        ("claim two", "contradicted", "sources disagree"),
        ("claim three", "not_enough_info", "sources are silent"),
        ("claim four", "entailed", "supported"),
    ]

    score, flagged = aggregate(claim_verdicts)

    assert score == 0.5
    assert flagged == [
        FlaggedClaim(claim="claim two", verdict="contradicted", reason="sources disagree"),
        FlaggedClaim(
            claim="claim three", verdict="not_enough_info", reason="sources are silent"
        ),
    ]


def test_aggregate_all_contradicted_returns_score_zero():
    claim_verdicts = [("claim", "contradicted", "false")]

    score, flagged = aggregate(claim_verdicts)

    assert score == 0.0
    assert len(flagged) == 1
