# Benchmark source and feasibility audit

Snapshot: 2026-07-16. This audit used upstream manifests, licenses, task
metadata, and resource declarations only. No approach scores or protected
solutions were viewed. Exact task IDs and hashes live in `research/selections/`.

## Locally calibratable without an account

### SWE-bench Verified

- Code source: `SWE-bench/SWE-bench` at
  `f7bbbb2ccdf479001d6467c9e34af59e44a840f9` (MIT).
- Dataset source: `princeton-nlp/SWE-bench_Verified` at
  `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`; the 500-row parquet payload is
  SHA-256 pinned in the selection manifest.
- Selection: 20 development and 50 evaluation IDs, repository-balanced and
  chosen by a score-blind deterministic hash rule.
- Remaining gate: build and oracle-run every selected official evaluator.

### Terminal-Bench 2

- Source: `harbor-framework/terminal-bench-2` at
  `2fd12b88aafdd04a52c298e3940bcb189f9766d6` (Apache-2.0).
- Selection: 6 development and 12 evaluation tasks, all non-easy and zero-GPU.
- Every `task.toml` and published Docker image is SHA-256 pinned. The task's
  own `allow_internet` setting is preserved equally across approaches.
- Remaining gate: pull each linux/amd64 image and oracle-run its Harbor
  verifier. Harbor itself does not require a hosted sandbox account.

## Frontier tracks with external prerequisites

### MLE-bench

- Source: `openai/mle-bench` at
  `507f92e1138bb6e40dac5c6ee7a6758e6424bf97` (MIT code; Kaggle datasets keep
  their own terms).
- Upstream says its 22-task Low split totals about 158 GB and data preparation
  requires Kaggle credentials plus accepted competition rules.
- The locked subset keeps only datasets at most 1 GB and excludes every Low
  task listed in upstream Known Issues. It is 3 development plus 6 evaluation
  tasks across six categories.
- This track cannot be calibrated anonymously. Do not redistribute prepared
  private data.

### RE-Bench

- Source: `METR/RE-Bench` at
  `93b98062e55f6945d4a7e213a3226dd419896170` (MIT).
- The development task declares 20 CPU and 100 GB RAM. Each evaluation task
  declares one H100, 13 CPU, and 100 GB RAM.
- Official solution archives were not extracted or inspected. Follow the
  upstream request not to publish protected solutions or send protected
  evaluation material to training APIs.
- This is an external-compute native-ceiling track, not a laptop benchmark.

### PaperBench Code-Dev

- Source: `openai/frontier-evals` at
  `51052cede8cc608f95bb00346635e03759013e5a` (MIT code).
- The chosen agent tasks do not require OpenAI or Hugging Face credentials.
  The official judge still requires model inference on the trusted grader
  host; that key is never mounted into a candidate container.
- Paper trees, configurations, and rubrics are hash-pinned. Rubrics and judge
  addenda remain sealed until an attempt ends.

## ActiveGraph-native suite

The framework is pinned at commit
`148e12c2969f18fa12a1a3c2e75f3affd9aa0616` and installed version 1.10.0.
The suite now contains five authored systems: incident coordination and
separation-of-duty approvals for development, then held-out quota scheduling,
revision provenance, and delegated access control. Every deliberate seed is
exactly 20/50 and every manager fixture oracle is 50/50 both on the host and in
the pinned no-network container. The remaining checks cover exact typed state,
relations, policy, composition, adversarial inputs, idempotency, and a real
cold runtime reload. This is evaluator calibration, not model evidence.

The sealed case generator is open source for reproducibility. During an
experiment the agent receives only the materialized public workspace, never
the repository root or manager grader directory. That is sufficient for this
preregistered local study, but it is not a durable secret-test leaderboard:
after release, an operator could inspect the generator manually.

## License conclusion

Ouroboros itself is MIT. That does not relicense external benchmark code,
datasets, papers, container images, or protected evaluation material. The
repository stores selection metadata and hashes; upstream assets stay in the
ignored `benchmark/.cache/` tree, generated ActiveGraph tasks stay in
`.benchmark-cache/`, and protected materials remain in official infrastructure.
