# Pdfabric

![PyPI](https://img.shields.io/pypi/v/pdfabric)
![PyPI - License](https://img.shields.io/pypi/l/pdfabric)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/pdfabric)
![Tests](https://github.com/hmiladhia/pdfabric/actions/workflows/quality.yml/badge.svg)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/copier-org/copier)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

PDF manipulation tools

## Quick Start

```
pip install pdfabric
```

## Usage

### Merge

Combine every top-level PDF in a directory into a single output PDF:

```
pdfabric merge DIRECTORY
```

- The files in `DIRECTORY` are merged in alphabetical order by filename; subdirectories are not recursed into.
- By default, the output is written next to `DIRECTORY`, named after it (e.g. merging `docs/invoices` writes `docs/invoices.pdf`).
- One bookmark per source file is added to the output by default, pointing at the first page that file contributed.

Options:

- `-o, --output PATH` — write the merged PDF to `PATH` instead of the default location.
- `-f, --force` — overwrite the output file if it already exists (by default the command refuses to overwrite an existing file).
- `--bookmarks / --no-bookmarks` — enable (default) or disable the per-file bookmarks.
- `--compress RATIO` — compress the merged output to approximately `RATIO` (a fraction between 0 and 1) of its pre-compression size, using the same target-ratio behavior as `pdfabric compress`. Off by default.

Example:

```
pdfabric merge ./invoices -o ./merged-invoices.pdf
pdfabric merge ./invoices -o ./merged-invoices.pdf --compress 0.5
```

### Compress

Shrink a PDF's file size:

```
pdfabric compress INPUT
```

- By default, the output is written next to `INPUT`, named after it (e.g. compressing `report.pdf` writes `report.compressed.pdf`).
- Three passes run by default: images are recompressed as JPEG (skipping bilevel, alpha-channel, and limited-palette images, which are never JPEG-recompressed), content streams are deflated, and identical objects are deduplicated.
- Image compression strength is controlled either directly (`--quality`/`--dpi`) or by a target size ratio (`--ratio`); the two styles cannot be combined.

Options:

- `-o, --output PATH` — write the compressed PDF to `PATH` instead of the default location.
- `-f, --force` — overwrite the output file if it already exists (by default the command refuses to overwrite an existing file).
- `--quality INT` — JPEG quality (0-100) for recompressed photographic images. Default: 80.
- `--dpi INT` — downsample images whose effective on-page DPI exceeds this cap. Default: 150.
- `--ratio FLOAT` — target output size as a fraction (0-1) of the input size; searches for a quality that reaches it, falling back to a best-effort result (and reporting the achieved ratio) if the target can't be reached. Cannot be combined with `--quality`/`--dpi`.
- `--images / --no-images` — enable (default) or disable the image recompression pass.
- `--streams / --no-streams` — enable (default) or disable the content-stream deflation pass.
- `--objects / --no-objects` — enable (default) or disable the identical-object deduplication pass.

Example:

```
pdfabric compress ./report.pdf --ratio 0.5
```

## Contribute
...
