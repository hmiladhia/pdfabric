# Proposal

## Why

pdfabric can merge PDFs but has no way to make one smaller. Scanned or photo-heavy PDFs are often far larger than they need to be, and the only options today are external tools (Acrobat, Ghostscript). A built-in `compress` command fills that gap and gives the existing `merge` command a way to shrink its own output in the same pass.

## What Changes

- New `pdfabric compress INPUT` CLI command and a matching `compress_file()` library function in a new `compress.py` module (mirrors `merge.py`'s pure-function + exception style).
- A shared compression engine with three independently toggleable passes:
  - **Images** (lossy, default on): recompress photographic images as JPEG at a given quality, and/or downsample images whose effective on-page DPI exceeds a given cap.
  - **Streams** (lossless, default on): deflate page content streams via `PdfWriter.compress_content_streams()`.
  - **Objects** (lossless, default on): dedupe identical indirect objects via `PdfWriter.compress_identical_objects()`.
- Two ways to control image compression strength, mutually exclusive:
  - `--quality INT` (0-100) and/or `--dpi INT` - direct, deterministic control.
  - `--ratio FLOAT` (0-1, fraction of original file size to target) - wraps quality in a bounded iterative search; if the target can't be reached without dropping quality below a floor, the command writes the best-effort result anyway and reports the achieved ratio instead of failing.
- Per-image classification before any lossy recompression is attempted: bilevel, limited-palette, and alpha-channel images are never JPEG-recompressed (JPEG has no alpha and does poorly on flat/sharp-edged content); only images classified as photographic are recompressed. This runs regardless of which control mode (`--quality`/`--dpi` vs `--ratio`) is used.
- DPI downsampling requires computing each image's effective on-page DPI from the content stream's transformation matrix (not provided by pypdf); when that extraction fails for a given image, that image falls back to quality-only handling instead of failing the whole run.
- New `-o/--output` and `-f/--force` options on `compress`, following the same conventions as `merge`.
- New `--compress RATIO` option added to the existing `merge` command: an optional, off-by-default shorthand that runs the full compression engine (ratio mode, all three passes) on the merged output before writing it, reusing `compress_file()`'s core.
- **New hard dependency**: Pillow, required for all image decode/recompress/classify operations.

## Capabilities

### New Capabilities
- `pdf-compress`: Shrinking a PDF's file size by recompressing its images (with per-image photographic/line-art/alpha classification and DPI-aware downsampling), deflating content streams, and deduplicating identical objects - controllable by direct quality/DPI or by a target size ratio, available as both a Python library call and a `pdfabric compress` CLI command.

### Modified Capabilities
- `pdf-merge`: adds an optional `--compress RATIO` option to the `pdfabric merge` CLI command that compresses the merged output before writing it.

## Impact

- `pyproject.toml`: add `pillow` to `dependencies`.
- `src/pdfabric/compress.py` (new): core compression engine and `compress_file()`.
- `src/pdfabric/merge.py`: `merge_files()`/`merge_directory()` gain an optional post-merge compression step driven by the new engine.
- `src/pdfabric/cli.py`: new `compress` command; `merge` command gains `--compress`.
- `README.md`: new "### Compress" section; "### Merge" section documents `--compress`.
- `tests/`: new `test_compress.py`; `test_merge.py` and `test_cli.py` gain cases for the new option/command.
