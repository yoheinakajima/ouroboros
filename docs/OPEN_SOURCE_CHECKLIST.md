# Open-source release checklist

The repository can be made public before headline benchmark execution, but the
research status must remain unmistakable.

## Required before the first public release

- [ ] Choose a repository license and add `LICENSE` (decision required: MIT or Apache-2.0).
- [ ] Confirm the project name and package name are available.
- [ ] Install from a clean Python 3.11+ environment with `pip install -e ".[dev]"`.
- [ ] Pass deterministic tests and lint in CI on a clean checkout.
- [ ] Confirm no `.env`, API key, private evaluator, hidden case, or local absolute path is tracked.
- [ ] Keep raw traces out of Git; publish curated summaries and attach selected redacted bundles to tagged releases.
- [ ] Review recovered v1.2 provenance and retained third-party notices.
- [ ] Add the repository URL to `CITATION.cff` after publication.
- [ ] Run the no-spend readiness report and publish its blockers honestly.

## Required before scored benchmark execution

- [ ] Implement the same brokered repo, terminal, and inference surface for all three approaches.
- [ ] Run each approach and grader in fresh containers with pinned image digests.
- [ ] Implement cold, evolved, and sham-control arms without deleting audit history.
- [x] Add bounded Hybrid author repair without exposing hidden cases.
- [ ] Add atomic multi-Pack trials.
- [ ] Give evolved v1.2 artifacts brokered model inference without credentials in their environment.
- [ ] Pin every upstream revision, dataset version, task ID, grader, and seed schedule.
- [ ] Audit task feasibility, grader validity, licenses, leakage, and compute requirements without observing scores.
- [ ] Freeze approach source hashes, prompts, docs corpus, model parameters, budgets, and retry rules.
- [ ] Set `execution_enabled` only in the freeze commit after independent protocol review.

## Required before making a recursive-improvement claim

- [ ] Complete at least five paired evolved/cold/sham replications per claim.
- [ ] Show uplift on distinct held-out B tasks after restart.
- [ ] Report uncertainty, failures, costs, regressions, and all excluded runs.
- [ ] Release enough traces and grader evidence for independent reproduction.
- [ ] Use “capability acquisition” or “self-extension” if causal uplift is not established.
