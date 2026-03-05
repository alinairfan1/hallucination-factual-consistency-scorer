---
version: 1
slug: "report-viewer"
primary_target: "report-viewer"
related_targets: []
---

# Surface Brief: Report Viewer

**Scope / visitor mode:** Operate. Single new page/app — read-only dashboard, no live scoring form.

**Audience / job:** Portfolio-first, dual audience. Reviewers (recruiters, technical interviewers) skim to
confirm the scorer is real and well-built within seconds. Operators/builders drill into individual examples
to verify claim-level reasoning and calibration.

**Action / task:** No write actions. Primary task is inspection: read the headline benchmark numbers, then
expand any example (benchmark or live-history) to see its claims, verdicts, and judge reasoning.

**Proof / content:** Real HaluEval benchmark results (Precision 87.0% / Recall 80.0% / F1 83.3% vs ~73.7%
naive baseline), the calibration table, and live `/v1/score` call history — all real, no fabricated data.
Caveats (small sample, imperfect calibration, one known unfixed failure case, dataset label noise) must
stay visible, not smoothed over.

**Chosen direction / memorable moment:** "The Evidence Docket" — dark, terminal-adjacent instrument panel.
Space Grotesk for structure, Space Mono for every number/claim/reasoning string. Verdict tags (entailed /
contradicted / not_enough_info) are the one signature device: pill-shaped, desaturated semantic color,
never reused elsewhere. See `DESIGN.md` for full tokens. The memorable moment: expanding any row reveals a
real judge transcript, not a re-stated summary.

**Unresolved decisions carried into build:**
- Exact API response shape for benchmark/live-history detail doesn't exist yet on the backend — frontend
  builds against typed mocks first, matching `PRODUCT.md`'s documented backend gap.
- Pagination/cap strategy for live-history list once real volume exists (not yet known).
