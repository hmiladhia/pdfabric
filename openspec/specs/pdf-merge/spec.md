# PDF Merge Specification

## Purpose

Combining multiple PDF files - from a directory of files or an explicit ordered list - into a single output PDF by appending their pages in order, available as both a Python library call and a `pdfabric merge` CLI command.

## Requirements

### Requirement: Merge a directory of PDFs into one file
The system SHALL combine every top-level file matching `*.pdf` or `*.PDF` in a given directory into a single output PDF, appending each file's pages in full and in order, with no other transformation of page content.

#### Scenario: Multiple PDFs merged in alphabetical order
- **WHEN** a directory contains `b.pdf`, `a.pdf`, and `c.pdf`
- **THEN** the output PDF contains all pages of `a.pdf`, followed by all pages of `b.pdf`, followed by all pages of `c.pdf`

#### Scenario: Non-PDF files are ignored
- **WHEN** a directory contains PDF files alongside files with other extensions (e.g. `.txt`, `.docx`)
- **THEN** only the `.pdf`/`.PDF` files are included in the merge

#### Scenario: Subdirectories are not recursed into
- **WHEN** a directory contains PDF files directly and also contains a subdirectory that itself contains PDF files
- **THEN** only the top-level PDF files are merged; PDFs inside the subdirectory are not included

#### Scenario: Directory has no PDF files
- **WHEN** the target directory contains zero files matching `*.pdf`/`*.PDF`
- **THEN** the operation fails with an error identifying that no PDF files were found, and no output file is written

#### Scenario: Target directory does not exist or is not a directory
- **WHEN** the given path does not exist, or exists but is not a directory
- **THEN** the operation fails with an error identifying the invalid path, and no output file is written

### Requirement: Merge an explicit ordered list of PDF files
The system SHALL also support merging a caller-supplied, explicitly ordered list of PDF file paths into a single output PDF, appending pages in the given order, for callers that already have their own ordering.

#### Scenario: Explicit list merged in given order
- **WHEN** a caller provides an ordered list `[c.pdf, a.pdf, b.pdf]`
- **THEN** the output PDF contains all pages of `c.pdf`, followed by `a.pdf`, followed by `b.pdf` - in that order, not alphabetically re-sorted

### Requirement: Default output location and name
When no explicit output path is given, the system SHALL write the merged PDF as a sibling of the source directory, named after the directory.

#### Scenario: Default output path derived from directory name
- **WHEN** merging directory `/docs/invoices` with no explicit output path
- **THEN** the output is written to `/docs/invoices.pdf`

### Requirement: Overwrite protection on output
The system SHALL refuse to overwrite an existing output file unless the caller explicitly requests it, to prevent accidental data loss.

#### Scenario: Existing output blocks the merge by default
- **WHEN** the resolved output path already exists and the caller has not requested a forced overwrite
- **THEN** the operation fails with an error identifying that the output already exists, and the existing file is left unmodified

#### Scenario: Forced overwrite replaces existing output
- **WHEN** the resolved output path already exists and the caller has requested a forced overwrite
- **THEN** the existing file is replaced with the newly merged PDF

### Requirement: Per-file bookmarks in the merged output
The system SHALL, by default, add one bookmark (outline entry) per source file to the merged output, pointing at the first page contributed by that file, and SHALL allow this behavior to be disabled.

#### Scenario: Bookmarks added by default
- **WHEN** a merge is performed without explicitly disabling bookmarks
- **THEN** the output PDF's outline contains one entry per source file, each pointing at the first page that file contributed, in the same order as the merged files

#### Scenario: Bookmarks explicitly disabled
- **WHEN** a merge is performed with bookmarks explicitly disabled
- **THEN** the output PDF's outline contains no entries added by the merge

#### Scenario: Bookmark title formatting
- **WHEN** a bookmark title is derived from a source filename stem (extension removed)
- **THEN** underscores and hyphens in the stem are replaced with spaces and the result is title-cased, e.g. `invoice_report_2024.pdf` produces the bookmark title "Invoice Report 2024", and `01-cover-letter.pdf` produces "01 Cover Letter"

### Requirement: CLI command for directory merge
The system SHALL expose the directory-merge capability as a `pdfabric merge DIRECTORY` command, with options controlling output path, overwrite, and bookmarks.

#### Scenario: Default invocation
- **WHEN** a user runs `pdfabric merge DIRECTORY` with no other options
- **THEN** the command merges `DIRECTORY`'s top-level PDFs alphabetically into the default output path, with bookmarks added, failing without overwriting if that output already exists

#### Scenario: Explicit output path
- **WHEN** a user runs `pdfabric merge DIRECTORY -o/--output PATH`
- **THEN** the merged PDF is written to `PATH` instead of the default location

#### Scenario: Forced overwrite via CLI
- **WHEN** a user runs `pdfabric merge DIRECTORY -f/--force` and the output path already exists
- **THEN** the existing file is overwritten instead of the command failing

#### Scenario: Bookmarks disabled via CLI
- **WHEN** a user runs `pdfabric merge DIRECTORY --no-bookmarks`
- **THEN** the merged PDF is produced with no outline entries added by the merge

#### Scenario: Command reports errors clearly and exits non-zero
- **WHEN** the underlying merge fails for any reason (invalid directory, no PDFs found, existing output without `--force`)
- **THEN** the CLI prints a clear, user-facing error message and exits with a non-zero status, without a Python traceback
