# Spec Delta

## MODIFIED Requirements

### Requirement: CLI command for directory merge
The system SHALL expose the directory-merge capability as a `pdfabric merge DIRECTORY` command, with options controlling output path, overwrite, bookmarks, and post-merge compression.

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

#### Scenario: Post-merge compression via CLI
- **WHEN** a user runs `pdfabric merge DIRECTORY --compress RATIO`
- **THEN** the merged output is compressed to approximately `RATIO` of its pre-compression size, using the same target-ratio compression behavior as the `pdfabric compress` command, before being written to the output path

#### Scenario: No post-merge compression by default
- **WHEN** a user runs `pdfabric merge DIRECTORY` without `--compress`
- **THEN** the merged output is written without any compression pass applied

#### Scenario: Command reports errors clearly and exits non-zero
- **WHEN** the underlying merge fails for any reason (invalid directory, no PDFs found, existing output without `--force`)
- **THEN** the CLI prints a clear, user-facing error message and exits with a non-zero status, without a Python traceback
