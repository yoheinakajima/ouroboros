# Paper release package

This directory is the version-controlled release package for:

> **When Self-Modification Becomes Memory: An Audited Comparison of Three
> Self-Improving Agent Substrates**

It contains the paper sources, appendix, figures, generated analysis tables,
masked update-proposal coding artifacts, adjudication ledger, analysis code,
and provenance controls. Complete run directories and raw traces are excluded
from Git because of size and disclosure risk. Their archival deposit is
described in [`ARTIFACT_ARCHIVE.md`](ARTIFACT_ARCHIVE.md).

`main.tex` is the canonical preprint source. `MANUSCRIPT.md` is a frozen,
readable companion snapshot and should only be changed together with a
regenerated and reviewed LaTeX source. arXiv fields are recorded in
[`ARXIV_METADATA.md`](ARXIV_METADATA.md).

## Verify the package

From the repository root:

```bash
python paper/scripts/scan_release.py --root paper --check
python paper/scripts/verify_manifest.py paper/provenance-manifest.json
```

Both commands exit nonzero on failure. The manifest verifier checks hashes,
byte counts, path safety, and whether any release file is missing from the
manifest.

The frozen figures and manuscript claims can also be regenerated or audited
from the included compact artifacts:

```bash
python paper/analysis/make_figures.py
python paper/analysis/reanalyze_equivalent_controls.py
python paper/analysis/audit_manuscript_style.py
python paper/analysis/audit_paper_links.py
python paper/analysis/audit_paper_claims.py
```

Scripts that reconstruct the compact tables or blinded coding packet from raw
trajectories require `--run-root` pointing to the separately archived complete
run deposit. They are retained here for methodological transparency; the
release package intentionally excludes raw traces pending the disclosure scan
described in `ARTIFACT_ARCHIVE.md`.

## Build the preprint

The release build expects Pandoc and Tectonic. Install the pinned
figure-conversion dependencies first:

```bash
python -m pip install -r paper/requirements.txt
python paper/scripts/convert_figures.py
```

Then build the paper:

```bash
bash paper/scripts/build_preprint.sh
```

The script writes the tracked release PDF to `paper/output/pdf/` and a delivery
copy to the repository-level `output/pdf/`. SVG-to-PDF conversion uses
`paper/scripts/convert_figures.py` with `svglib` and ReportLab.

## Rebuild release metadata

After an intentional paper edit:

```bash
python paper/scripts/scan_release.py --root paper --write-report paper/scan-report.json
python paper/scripts/build_manifest.py --root paper --output paper/provenance-manifest.json
python paper/scripts/verify_manifest.py paper/provenance-manifest.json
```

## Licenses

- Repository code: MIT, as specified in the root [`LICENSE`](../LICENSE).
- Paper text, tables, and original figures: CC BY 4.0, as specified in
  [`LICENSE-CC-BY-4.0.md`](LICENSE-CC-BY-4.0.md).
- Third-party benchmark names and cited works remain the property of their
  respective owners.
