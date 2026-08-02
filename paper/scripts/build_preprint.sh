#!/usr/bin/env bash
set -euo pipefail

paper_root="$(cd "$(dirname "$0")/.." && pwd)"
repo_root="$(cd "$paper_root/.." && pwd)"
pandoc_bin="${OUROBOROS_PANDOC:-pandoc}"
tectonic_bin="${OUROBOROS_TECTONIC:-tectonic}"

"$pandoc_bin" \
  "$paper_root/MANUSCRIPT.md" \
  "$paper_root/APPENDIX_START.md" \
  "$paper_root/APPENDIX.md" \
  --from=markdown+pipe_tables+raw_tex+tex_math_single_backslash \
  --to=latex \
  --standalone \
  --natbib \
  --bibliography="$paper_root/references.bib" \
  --lua-filter="$paper_root/latex_filter.lua" \
  --template="$paper_root/template.tex" \
  --output="$paper_root/main.tex"

build_dir="$paper_root/tmp/latex"
mkdir -p "$build_dir" "$paper_root/output/pdf" "$repo_root/output/pdf"
"$tectonic_bin" \
  --keep-logs \
  --keep-intermediates \
  --outdir "$build_dir" \
  "$paper_root/main.tex"

cp "$build_dir/main.pdf" \
  "$paper_root/output/pdf/when-self-modification-becomes-memory.pdf"
cp "$paper_root/output/pdf/when-self-modification-becomes-memory.pdf" \
  "$repo_root/output/pdf/when-self-modification-becomes-memory.pdf"
