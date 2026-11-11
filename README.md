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

Example:

```
pdfabric merge ./invoices -o ./merged-invoices.pdf
```

## Contribute
...
