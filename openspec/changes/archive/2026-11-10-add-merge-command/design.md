# Design

## Context

`pdfabric` is currently an empty copier-generated scaffold (`src/pdfabric/__init__.py` with just a version, `src/pdfabric/__main__.py` printing a placeholder). No dependencies beyond dev/test tooling are declared in `pyproject.toml`; there is no `click`, no PDF library, no `[project.scripts]` entry point. This is the first real capability, so it also establishes the project's library/CLI split that later commands (split, rotate, watermark, etc.) are expected to follow. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Establish a reusable pattern: a pure-Python library module containing the actual logic, with a thin `click`-based CLI module that only translates arguments and exceptions.
- Keep the merge operation itself dependency-light and free of native/non-Python build requirements.

**Non-Goals:**
- No bookmark/outline merging *from* the source PDFs themselves (only the new synthetic one-per-file bookmark described in the spec) - no metadata merging, no page transformation (rotation, scaling, OCR), no recursive directory scanning. These are explicitly out of scope per the proposal and may become separate future capabilities.

## Decisions

### PDF engine: `pypdf`
Chosen over `pikepdf` and `PyMuPDF`:
- `pikepdf` wraps the native `qpdf` C++ library. It's excellent at repairing malformed PDFs, but that's not a requirement here, and it adds a compiled dependency the project doesn't otherwise need.
- `PyMuPDF` (`fitz`) is AGPL/commercial dual-licensed. Pulling it in as a runtime dependency of an MIT-licensed package imposes AGPL obligations on anyone installing `pdfabric`, which is an unacceptable license conflict for a general-purpose dependency.
- `pypdf` is pure Python, BSD-licensed (compatible with MIT), actively maintained, and its `PdfWriter.append()` + `add_outline_item()` API maps directly onto "concatenate pages" and "add a bookmark at a page" with no extra work.

### Module layout
- `pdfabric/merge.py`: `merge_files(paths, output, *, force=False, add_bookmarks=True)` (explicit ordered list - the core primitive) and `merge_directory(directory, output=None, *, force=False, add_bookmarks=True)` (directory convenience wrapper: lists, filters, sorts, then delegates to `merge_files`).
- `pdfabric/cli.py`: `click.group()` named `pdfabric` with a `merge` subcommand calling `merge_directory`, catching the library's exceptions and re-raising as `click.ClickException` with a clean message (no traceback, exit code 1).
- `pdfabric/__main__.py`: reduced to invoking the CLI group, replacing the current placeholder.
- `pyproject.toml`: add `click` and `pypdf` to `[project.dependencies]`, add `[project.scripts] pdfabric = "pdfabric.cli:main"`.

### Error signaling: plain built-in exceptions from the library, mapped to CLI errors at the boundary
`merge_directory`/`merge_files` raise standard library exceptions (`NotADirectoryError`/`FileNotFoundError` for a bad directory, `ValueError` for "no PDFs found", `FileExistsError` for an output collision without `force`). This keeps the library usable and testable independent of `click`. `cli.py` is the only place that catches these and converts them to `click.ClickException` messages - the library itself never imports `click`.

### Bookmark title derivation as a small pure function
`_format_bookmark_title(stem: str) -> str` (private to `merge.py`): replace `_` and `-` with spaces, then `str.title()`. Kept as an isolated, directly unit-testable function since the exact formatting rule (spec: "Bookmark title formatting") is a precise, easy-to-regress piece of logic.

### Output path resolution and overwrite check happen before any merge work
`merge_directory` resolves the default output path (`directory.parent / f"{directory.name}.pdf"`) and checks for an existing file at that path *before* opening/merging any input PDFs, so a collision is reported immediately rather than after doing the (possibly expensive) merge work.

## Risks / Trade-offs

- [Plain alphabetical (lexicographic) sort means `file2.pdf` sorts after `file10.pdf`] -> Accepted as-is: this matches what the user explicitly asked for ("sorted alphabetically"). A natural/numeric sort option can be added later as a flag if it turns out to be needed; not introducing it now avoids guessing at unrequested behavior.
- [`pypdf`'s `PdfWriter.append()` loads each source file fully; very large directories of large PDFs could use significant memory] -> Accepted for v1; no streaming merge exists in `pypdf` that would meaningfully change this, and it's not a stated requirement.
- [Case-insensitive `*.pdf` matching could double-count a file if a filesystem allows both `a.pdf` and `a.PDF` to coexist (case-sensitive filesystems only)] -> Each is a distinct file and both are legitimately merged; no special-casing needed since this is not a collision, just two different input files.
