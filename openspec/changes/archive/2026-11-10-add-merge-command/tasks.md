# Tasks

## 1. Dependencies

- [x] 1.1 Add `click` and `pypdf` to `[project.dependencies]` in `pyproject.toml`; verify `pip install -e .` (or `uv sync`) succeeds and `python -c "import click, pypdf"` runs without error.

## 2. Merge library (`pdfabric/merge.py`)

- [x] 2.1 Implement `_format_bookmark_title(stem: str) -> str` (replace `_`/`-` with spaces, then title-case); add unit tests covering `invoice_report_2024` -> `Invoice Report 2024`, `01-cover-letter` -> `01 Cover Letter`, and a plain name passing through unchanged; verify tests pass.
- [x] 2.2 Implement `merge_files(paths, output, *, force=False, add_bookmarks=True)`: append pages from each path in the given order via `pypdf.PdfWriter`, add one outline entry per file at its first page when `add_bookmarks` is true, raise `FileExistsError` if `output` already exists and `force` is false; add unit tests for page ordering, bookmark presence/absence, and overwrite protection/force; verify tests pass.
- [x] 2.3 Implement `merge_directory(directory, output=None, *, force=False, add_bookmarks=True)`: validate `directory` exists and is a directory (else raise `FileNotFoundError`/`NotADirectoryError`), list top-level `*.pdf`/`*.PDF` files (no recursion), raise `ValueError` if none found, sort the list alphabetically, resolve `output` to `directory.parent / f"{directory.name}.pdf"` when not given, then delegate to `merge_files`; add unit tests for alphabetical ordering, non-PDF files being ignored, subdirectories being ignored, the empty-directory error, the missing-directory error, and the default output path; verify tests pass.

## 3. CLI (`pdfabric/cli.py`, `pdfabric/__main__.py`, entry point)

- [x] 3.1 Implement a `click.group()` named `pdfabric` with a `merge` subcommand taking a `DIRECTORY` argument and `-o/--output`, `-f/--force`, `--bookmarks/--no-bookmarks` (default: bookmarks on) options, calling `merge_directory` and catching `FileNotFoundError`/`NotADirectoryError`/`ValueError`/`FileExistsError` to re-raise as `click.ClickException` with a clear message; add CLI tests using `click.testing.CliRunner` covering default invocation, `-o`, `-f` overwrite, `--no-bookmarks`, and each error path exiting non-zero with no Python traceback; verify tests pass.
- [x] 3.2 Update `pdfabric/__main__.py` to invoke the `pdfabric` CLI group instead of the current placeholder greeting; verify `python -m pdfabric merge --help` runs the new command.
- [x] 3.3 Add `[project.scripts]` entry `pdfabric = "pdfabric.cli:main"` to `pyproject.toml`; verify `pip install -e .` exposes a `pdfabric` command and `pdfabric merge --help` runs successfully from the shell.

## 4. Documentation

- [x] 4.1 Add a "Usage" section to `README.md` documenting `pdfabric merge DIRECTORY`, its options, the default output naming/location rule, and the bookmark behavior, with a short example; verify the documented example command runs as written against a sample directory of PDFs.
