# Tasks

## 1. Dependency and module setup

- [x] 1.1 Add `pillow` to `pyproject.toml` `dependencies`, and verify `uv sync` (or `pip install -e .`) resolves it with no conflicts
- [x] 1.2 Create the `src/pdfabric/compress.py` module skeleton (imports, `StrPath` alias matching `merge.py`), and verify `python -c "import pdfabric.compress"` succeeds

## 2. Image classification

- [x] 2.1 Implement an image classifier (bilevel / alpha / limited-palette / photographic) per design Decision 3, operating on a PIL `Image`, and verify unit tests in `tests/test_compress.py` cover a 1-bit image, an RGBA image, a <=256-color palette image, and a many-color RGB image each landing in the correct category

## 3. Effective on-page DPI

- [x] 3.1 Implement the content-stream CTM walk (tracking `q`/`Q`/`cm`, yielding the matrix in effect at each image-drawing `Do`) per design Decision 4, and verify unit tests cover an untransformed image, a scaled image, and an image nested inside a `q`/`Q` pair
- [x] 3.2 Implement effective-DPI computation from a placement's CTM and the image's pixel dimensions, and verify a unit test asserts the known DPI of a constructed placement (e.g. a 100x100px image placed in a 1in x 1in box on the page yields 100 DPI)
- [x] 3.3 Wrap the CTM walk in error handling that reports "DPI unknown" for that image instead of raising, and verify a unit test feeds a page with an unsupported/malformed content stream and gets that graceful result rather than an exception

## 4. Image pass

- [x] 4.1 Implement the image pass over a `PdfWriter`: for each image on each page, classify it (task 2.1), compute its effective DPI (task 3), downsample it when a DPI cap applies and is exceeded, and recompress it via `ImageFile.replace(..., quality=...)` only when classified as photographic, and verify unit tests assert a photographic image's re-encoded size shrinks at a lower quality while a bilevel/alpha/limited-palette image's bytes are left unchanged
- [x] 4.2 Verify a unit test asserts a DPI-capped oversized image is downsampled to the expected pixel dimensions, and an image already under the cap keeps its original pixel dimensions
- [x] 4.3 Verify a unit test asserts that when no quality/DPI is given, the default quality (80) and default DPI cap (150) from `specs/pdf-compress/spec.md` are applied

## 5. Writer-level compression engine and path-level `compress_file`

- [x] 5.1 Implement a writer-level compression function operating directly on a `PdfWriter` (image pass from task 4, plus `compress_content_streams()`/`compress_identical_objects()`), each pass gated by its own flag, so it can be reused by both file-based compression and `merge --compress`, and verify a unit test exercises it directly against a `PdfWriter` instance
- [x] 5.2 Implement `compress_file(input_path, output=None, *, quality=None, dpi=None, images=True, streams=True, objects=True, force=False) -> Path`, wrapping the writer-level engine with path I/O, default output path (`<stem>.compressed.pdf`, sibling of input), and overwrite protection matching `merge.py`'s pattern, and verify unit tests cover: default output path, `FileExistsError` without `force`, overwrite with `force`, and `FileNotFoundError` for a missing input
- [x] 5.3 Verify a unit test asserts each pass's on/off flag independently changes (or, when off, does not change) the output

## 6. Ratio mode

- [x] 6.1 Implement the bounded binary-search ratio mode (quality floor 20, ceiling 95, up to 8 iterations, 2% early-exit tolerance) per design Decision 6, rebuilding the writer from the original input each iteration, exposed as `compress_file(..., ratio=...)`, and verify a unit test with a synthetic photographic-image PDF converges to within the documented tolerance of a target ratio
- [x] 6.2 Implement the best-effort fallback when the floor is reached without hitting the target (write the floor-quality result, report the achieved ratio instead of raising), and verify a unit test asserts output is still written and the achieved ratio is reported when the target is unreachable
- [x] 6.3 Verify a unit test asserts `ratio` combined with `quality` or `dpi` raises `ValueError` before any output file is written

## 7. CLI `compress` command

- [x] 7.1 Add the `compress` command to `cli.py` (`-o/--output`, `-f/--force`, `--quality`, `--dpi`, `--ratio`, `--images/--no-images`, `--streams/--no-streams`, `--objects/--no-objects`), reusing `merge`'s `click.ClickException` error-handling pattern, and verify CLI tests in `tests/test_cli.py` (matching its existing `CliRunner` style) cover default invocation, explicit output, `--force`, and a clear non-zero exit without a traceback for each documented error case (bad path, existing output, `--ratio` with `--quality`/`--dpi`)
- [x] 7.2 Document the command in `README.md` under a new "### Compress" section matching the "### Merge" section's style and options-list format, and verify the documented example command runs as written

## 8. `merge --compress` integration

- [x] 8.1 Add `--compress RATIO` to the `merge` CLI command and thread it through `merge_files`/`merge_directory`: after building the merged `PdfWriter`, apply the ratio-mode writer-level engine (task 6) before writing the output, and verify unit tests assert `merge(..., compress=RATIO)` produces an output smaller than the uncompressed merge on a fixture containing a compressible photographic image, while `merge(...)` without `compress` is unaffected
- [x] 8.2 Document `--compress` in `README.md`'s "### Merge" section with an example, and verify the documented example runs as written

## 9. Full verification

- [x] 9.1 Run the full test suite (`pytest`) and linters (`ruff check`, `ruff format --check`, `mypy`) and verify all pass

## Workflow follow-up

- Archive this change once implementation and verification above are complete.
