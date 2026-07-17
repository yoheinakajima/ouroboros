# Local run artifacts

Raw traces, generated source, hidden pilot fixtures, subprocess logs, and
benchmark workspaces are intentionally excluded from Git. They can contain
large SQLite databases, external benchmark data, absolute machine paths, and
evaluation material that should not become training data.

The research harness writes complete immutable runs here by default. Curated,
secret-free summaries belong under `evidence/`; full bundles intended for
publication should be checksummed and attached to a tagged release.

Historical artifacts that remain in earlier Git commits are evidence from the
prototype phase, not the storage policy for new experiments.
