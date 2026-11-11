# Proposal

## Why

`pdfabric` currently has no PDF manipulation capability at all — it's an empty scaffold. The most common first need is combining a folder of separately scanned/exported PDFs (e.g. invoices, chapters, signed pages) into one document. This establishes the project's core pattern (library function + thin CLI wrapper) that later commands (split, rotate, watermark, etc.) will follow.

## What Changes

- New library function `pdfabric.merge.merge_directory(directory, output=None, *, force=False, add_bookmarks=True)` that concatenates every top-level `*.pdf`/`*.PDF` file in a directory, sorted alphabetically by filename, into one output PDF — pages only, no per-file transformation.
- New lower-level `pdfabric.merge.merge_files(paths, output, *, add_bookmarks=True)` for callers who already have an explicit, ordered list of files.
- New CLI command `pdfabric merge DIRECTORY [-o/--output PATH] [-f/--force] [--bookmarks/--no-bookmarks]` wrapping `merge_directory`.
- Output defaults to `directory.parent / f"{directory.name}.pdf"` (sibling to the source directory).
- Existing output file is left untouched (command errors) unless `--force` is passed.
- When bookmarks are enabled (default), one flat outline entry per source file is added to the output, pointing at the first page that file contributes. The title is derived from the filename stem with underscores/hyphens replaced by spaces and the result title-cased (e.g. `invoice_report_2024.pdf` -> "Invoice Report 2024").
- Adds `click` (CLI) and `pypdf` (PDF engine) as runtime dependencies.

## Capabilities

### New Capabilities
- `pdf-merge`: Combining multiple PDF files — from a directory or an explicit file list — into a single output PDF, with optional per-file bookmarks, exposed as both a library function and a CLI command.

### Modified Capabilities
(none — first capability in the project)

## Impact

- New dependencies: `click`, `pypdf` (to be added to `pyproject.toml`).
- New modules: `src/pdfabric/cli.py`, `src/pdfabric/merge.py`.
- `src/pdfabric/__main__.py` changes from the placeholder "Hello from pdfabric!" to invoke the new CLI group.
- `pyproject.toml` gains a `[project.scripts]` entry point (`pdfabric = "pdfabric.cli:main"` or equivalent) so the CLI is installable as a command.
- No breaking changes — this is new, additive functionality in an otherwise-empty package.
