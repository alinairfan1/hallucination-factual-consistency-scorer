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

100 examples total (50 supported, 50 hallucinated). Regenerate with:

```bash
python3 -m scripts.prepare_halueval_subset --limit 50 --output data/halueval_qa_benchmark.jsonl
```

See HaluEval's repository for the original dataset and its MIT license terms.
