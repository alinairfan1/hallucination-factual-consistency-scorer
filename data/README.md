# Benchmark dataset

`halueval_qa_benchmark.jsonl` is derived from the QA subset of
[HaluEval](https://github.com/RUCAIBox/HaluEval) (RUCAIBox), MIT License.

Each of the first 50 rows of HaluEval's `data/qa_data.json` was converted into
two examples in this project's `scorer.dataset.DatasetExample` JSONL shape
(`answer`, `sources`, `label`):

- `label: "supported"` — HaluEval's `right_answer` for that row, grounded
  against HaluEval's `knowledge` field as the single source.
- `label: "hallucinated"` — HaluEval's `hallucinated_answer` for the same row,
  grounded against the same `knowledge` source.

HaluEval's `right_answer` and `hallucinated_answer` are short-answer QA spans
(e.g. `"Delhi"`) taken from HotpotQA — they are only checkable propositions in
the context of their question ("the answer to '...what city?' is Delhi"), not
on their own. So both answer texts are folded into their row's `question`
before being written out, uniformly across both labels:

```
Question: "<question>" Answer: <right_answer or hallucinated_answer>
```

An earlier version of this script wrote `right_answer`/`hallucinated_answer`
directly into `answer` with no question. That made the two classes trivially
separable by answer length alone (HotpotQA short-answer spans are typically
1-3 words; HaluEval's fabricated `hallucinated_answer` text is a full
sentence), so a judge that did zero fact-checking and only measured answer
length scored ~99% F1 on it. Folding in the question removes that confound
by making every `answer` string share the same "Question: ... Answer: ..."
scaffolding regardless of label.

**Known limitation:** this does not make the dataset airtight against a
length heuristic — it only makes the discrepancy inherent to HaluEval's raw
text, rather than one introduced by this project's conversion. HaluEval's
fabricated `hallucinated_answer` sentences still tend to be more verbose than
its terse correct short answers even after the question is folded in on both
sides. Sweeping every possible single length-threshold classifier over the
100 reformatted examples in this file yields a best achievable F1 of ~73.7%
(vs. ~99% before this fix) — nowhere near "solved" but no longer trivial
either. Real benchmark results from this dataset should be interpreted with
that ceiling in mind: a live scorer run's F1 is only meaningful evidence of
real fact-checking if it clearly exceeds what a length-only classifier could
achieve (~73.7%), not just the "always supported" naive baseline (0% F1,
since every real run includes hallucinated examples).

100 examples total (50 supported, 50 hallucinated). Regenerate with:

```bash
python3 -m scripts.prepare_halueval_subset --limit 50 --output data/halueval_qa_benchmark.jsonl
```

See HaluEval's repository for the original dataset and its MIT license terms.
