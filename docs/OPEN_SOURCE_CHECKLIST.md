# Open-source release checklist

The repository can be made public before headline benchmark execution, but the
research status must remain unmistakable.

## Required before the first public release

- [x] Choose a repository license and add `LICENSE` (MIT).
- [x] Confirm the public repository (`yoheinakajima/ouroboros`) and PyPI package name (`ouroboros-activegraph`, unclaimed as of 2026-07-16).
- [x] Build sdist/wheel in isolated environments and install/run the wheel in a fresh Python 3.11 venv.
- [ ] Pass deterministic tests and lint in CI on a clean checkout.
- [x] Confirm `.env` and benchmark caches are ignored and scan tracked inputs for keys and local absolute paths.
- [x] Keep raw traces out of Git; only `artifacts/README.md` is tracked under `artifacts/`.
- [x] Review recovered v1.2 provenance: byte-pinned files come from Yohei Nakajima's `cc5bb62`; no vendored third-party source was found in the recovered pair.
- [x] Add the public repository URL to `CITATION.cff`.
- [ ] Run the no-spend readiness report and publish its blockers honestly.

## Required before scored benchmark execution

- [x] Implement the same brokered repo, terminal, and inference surface for all three approaches.
- [x] Implement fresh, digest-pinned candidate-command and sealed-grader containers.
- [ ] Run one no-score end-to-end calibration attempt through each real architecture adapter.
- [x] Implement cold, evolved, and sham-control arms without deleting audit history.
- [x] Add bounded Hybrid author repair without exposing hidden cases.
- [x] Add atomic multi-Pack trials.
- [x] Give evolved v1.2 artifacts brokered model inference without credentials in their environment.
- [x] Pin candidate upstream revisions and score-blind task selections for calibration.
- [x] Audit licenses, leakage warnings, and compute/data requirements without observing scores.
- [ ] Oracle-calibrate every selected task and freeze exact grader revisions and seed schedules.
- [ ] Freeze approach source hashes, prompts, docs corpus, model parameters, budgets, and retry rules.
- [ ] Set `execution_enabled` only in the freeze commit after independent protocol review.

## Required before making a recursive-improvement claim

- [ ] Complete at least five paired evolved/cold/sham replications per claim.
- [ ] Show uplift on distinct held-out B tasks after restart.
- [ ] Report uncertainty, failures, costs, regressions, and all excluded runs.
- [ ] Release enough traces and grader evidence for independent reproduction.
- [ ] Use “capability acquisition” or “self-extension” if causal uplift is not established.
