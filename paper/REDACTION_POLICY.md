# Release redaction and exclusion policy

Version: 1.0  
Date: 2026-07-23

## Scope

Every text file in this release package is scanned for credential patterns,
private-key material, email addresses, IP addresses, user-home paths, and
common account-token formats. The recorded scan result is
[`scan-report.json`](scan-report.json).

## Applied redactions

Two generated JSON artifacts contained absolute local user-home paths:

1. `data/generated/posthoc-metrics.json`
2. `data/taxonomy/coder-agreement.json`

The release copies replace the local study-root path with `<RELEASE_ROOT>` and
replace the two original coder-label paths with release-relative paths. No
scores, labels, statistical outputs, hashes of source evidence, or substantive
text were changed.

The original frozen local artifacts remain unchanged.

## Exclusions

The following are excluded from Git:

- `.env` files and credentials;
- complete task workspaces and container filesystems;
- raw request and response traces;
- raw tool transcripts;
- external benchmark caches and images;
- full recovery and grader directory trees.

Those materials are intended for a separately scanned immutable archive. Its
DOI is pending. Exclusion from Git is based on size and disclosure risk and
does not imply that the evidence was discarded.

## Scan policy

A passing scan requires zero unreviewed findings. Findings are never
allowlisted merely because they occur in generated data. A necessary path
redaction must preserve the semantic value, be described above, and be
recorded in the provenance manifest.

