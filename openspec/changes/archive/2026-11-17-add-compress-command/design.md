# Design

## Context

`merge.py` establishes the pattern this change follows: a pure library function operating on `pathlib.Path`s, raising plain built-in exceptions, with a thin `cli.py` wrapper that catches them and re-raises as `click.ClickException`. The only current dependencies are `click`, `cryptography`, and `pypdf`.

pypdf 7.0.1 (the installed version) provides the building blocks but not a ready-made "compress a PDF" operation:
- `PdfWriter.compress_content_streams()` and `PdfWriter.compress_identical_objects()` exist and are lossless, dependency-free.
- Image recompression exists only as `ImageFile.replace(new_image, **save_kwargs)` on `page.images[i]`, which requires the image to belong to a `PdfWriter` (not a bare `PdfReader`) and requires Pillow - verified by import: `pypdf.generic._image_xobject` raises `ImportError` without it.
- There is no helper for an image's *effective on-page DPI*. Getting it requires walking the page's content stream, tracking the CTM through `cm`/`q`/`Q`, and reading the matrix in effect at each `Do` operator that draws the image XObject. pypdf's `Transformation` class (`_page.py`) provides the matrix math (`matrix_multiply`, the 3x3 form) but not the walk itself.

See `proposal.md` - Why / What Changes for motivation and scope; see `specs/pdf-compress/spec.md` and `specs/pdf-merge/spec.md` for the externally observable behavior this design implements.

## Goals / Non-Goals

**Goals:**
- A single compression engine (`compress.py`) that both the `compress` command and `merge --compress` call, so the two never drift.
- Image recompression that is safe by default: never silently degrade line art, text scans, or transparency.
- A ratio-targeting mode built on top of the same quality/DPI primitives used in direct mode, not a separate code path.

**Non-Goals:**
- Font subsetting, metadata stripping, or structural optimizations (unused object pruning beyond `compress_identical_objects()`) - out of scope for this change.
- Exact ratio guarantees - ratio mode is best-effort search, not a solver.
- Re-encoding non-JPEG-suitable images into some other lossless-but-smaller format (e.g. re-palettizing PNG-like XObjects) - the streams/objects passes are the only lossless levers in this change.

## Decisions

### 1. Module shape: mirror `merge.py`
`compress.py` exposes `compress_file(input_path, output=None, *, quality=None, dpi=None, ratio=None, images=True, streams=True, objects=True, force=False) -> Path`, raising `FileNotFoundError`, `ValueError` (bad combination of options, e.g. `ratio` with `quality`/`dpi`), and `FileExistsError` (output exists, no `force`) - the same exception vocabulary `cli.py` already catches for `merge`. `cli.py`'s `except` clause for the new `compress` command reuses that tuple.

Rationale: keeps the codebase's one established pattern instead of introducing a second convention. Alternative considered: a class-based `Compressor` with configurable passes - rejected as unneeded ceremony for three passes and one entry point.

### 2. Pass ordering and independence
Passes run in a fixed order: images -> streams -> objects. Each pass is a plain function taking a `PdfWriter` and returning nothing (mutates in place), gated by its own boolean flag in `compress_file`. Images first because content-stream deflation and object dedup are cheap and should see the final (possibly replaced) image objects; order between streams and objects doesn't matter functionally since neither touches image data, but running objects last means dedup sees any duplicate image objects left after image replacement.

### 3. Image classification heuristic
For each image returned by `page.images`, classify before considering lossy recompression, using only the PIL `Image` already loaded onto `ImageFile.image`:
- **Bilevel**: `image.mode == "1"` -> never recompress.
- **Alpha**: `image.mode in ("RGBA", "LA", "PA")` or `"transparency" in image.info` -> never recompress (JPEG has no alpha channel; silently flattening would change appearance).
- **Limited palette**: `image.getcolors(maxcolors=256) is not None` (i.e. 256 or fewer unique colors) -> treat as line art/screenshot, never recompress as JPEG.
- **Photographic**: everything else -> eligible for JPEG recompression.

`getcolors()` with a `maxcolors` bound is O(pixels) but bounded and cheap relative to re-encoding; it already returns `None` early when the count exceeds the bound, so this does not become a full histogram scan on large photos.

Alternative considered: classify from the PDF's declared `/ColorSpace`/`/BitsPerComponent` instead of decoding pixels. Rejected - a photo can be stored as indexed color, and declared bit depth doesn't reveal whether an RGB image is actually flat-color line art; decoding the already-loaded `Image` is both more accurate and no extra I/O since pypdf decodes it anyway to populate `ImageFile.image`.

### 4. Effective on-page DPI via CTM walk
A new helper, `_iter_image_placements(page)`, tokenizes the page's content stream operators (reusing `pypdf.generic.ContentStream`, which pypdf already uses internally for parsing), maintains a CTM stack (push on `q`, pop on `Q`, multiply on `cm`), and yields `(image_name, ctm)` for each `Do` operator whose operand names an image XObject. The image's displayed width/height in PDF user-space units comes from applying that CTM to the unit square; combined with the XObject's pixel `/Width`/`/Height`, effective DPI = `pixels / (user_space_units / 72)` per axis (using the smaller of the two axes, i.e. the more conservative/higher DPI estimate, when they differ).

If an image is referenced from inside a nested Form XObject, or any operator in the walk is malformed/unsupported, the walk aborts **for that image only** and `compress_file` falls back to quality-only handling for it (per `specs/pdf-compress/spec.md` - "Effective DPI cannot be determined for an image"). This keeps DPI capping best-effort rather than a run-wide failure mode.

Alternative considered: render each page to a bitmap (e.g. via an external renderer) and measure - rejected as a far heavier dependency and slower than a direct content-stream walk for a feature that's explicitly best-effort already.

### 5. Quality/DPI application via `ImageFile.replace`
For an image classified as photographic:
1. If a DPI cap applies and the computed effective DPI exceeds it, resize the PIL image down to the pixel dimensions implied by the cap (`Image.resize`, `Image.Resampling.LANCZOS`) before re-encoding.
2. Call `page_image.replace(resized_or_original, quality=effective_quality)`. `quality` is passed straight through as a `Pillow.Image.save()` kwarg, which `ImageFile.replace` already forwards (verified in pypdf source).

### 6. Ratio mode: bounded binary search over quality
`compress_file(..., ratio=R)` runs the full pipeline repeatedly: binary search over quality in `[20, 95]` (20 = quality floor, chosen as the point below which JPEG artifacts become hard to call "compressed" rather than "broken"; 95 as a practical ceiling since higher rarely changes size), DPI cap held fixed at the default (150) for the duration of the search since varying two dimensions at once makes the search non-monotonic. Up to 8 iterations (giving ~1/256 resolution on the quality range, well under one quality unit) or early-exit once within 2% of the target ratio. Each iteration re-runs the pipeline against a fresh copy of the writer (rebuilt from the original input) rather than mutating cumulatively, since JPEG re-encoding is not idempotent/reversible.

If the search's best achieved ratio at the floor quality is still above the target, `compress_file` writes that best-effort result and returns an achieved-ratio value (surfaced by the CLI as a warning message) instead of raising - per spec, this is "best-effort + report," not failure.

Alternative considered: linear search / fixed quality ladder (e.g. try 90, 70, 50, 30) - rejected as needing more iterations for similar precision and being less predictable in iteration count than binary search.

### 7. `merge --compress RATIO` reuses `compress_file`
`merge_directory`/`merge_files` write the merged `PdfWriter` to a temporary in-memory buffer (`io.BytesIO`) when `--compress` is given, then call `compress_file`'s underlying ratio-mode pipeline function directly (not round-tripping through the CLI), passing all three passes enabled. `--compress` on `merge` only exposes the ratio control, not quality/DPI, per the proposal's "shorthand" framing - keeping `merge`'s option surface small.

### 8. New dependency: Pillow as hard dependency
Added directly to `pyproject.toml` `dependencies`, not an optional extra - per the proposal and prior discussion, since compression is the point of the `compress` command and splitting install paths (`pdfabric` vs `pdfabric[compress]`) adds packaging complexity disproportionate to Pillow's install size.

## Risks / Trade-offs

- **[Risk]** The CTM-walk for effective DPI is new, non-trivial parsing logic with no pypdf helper to lean on; edge cases (rotated images, non-uniform scale, images drawn via nested Form XObjects or patterns) are easy to miss. → Mitigation: per-image try/except around the walk with quality-only fallback (Decision 4) means a parsing gap degrades gracefully (less compression on that image) rather than crashing the run; cover rotated/scaled/nested cases explicitly in tests rather than assuming the simple case generalizes.
- **[Risk]** `getcolors(maxcolors=256)` as the line-art/photo boundary is a heuristic, not a guarantee - a low-color photographic image (e.g. a solid-background product photo) could be skipped when recompressing it would have been fine, and a noisy scan with >256 colors could be JPEG-recompressed and lose text sharpness. → Mitigation: this is the documented, intentional "cautious by default" trade-off from the proposal; no mitigation beyond documenting the heuristic's boundary in the README.
- **[Risk]** Rebuilding the writer from scratch on every binary-search iteration (Decision 6) means ratio mode's cost scales with iteration count (up to 8x a single-pass compress) on large files. → Mitigation: bound iterations at 8 and early-exit within 2% of target; document that `--ratio` is slower than `--quality`/`--dpi` in the README.
- **[Risk]** Pillow as a new hard dependency increases install size for users who only ever use `merge`. → Mitigation: accepted trade-off per Decision 8; Pillow is a common, well-maintained dependency with prebuilt wheels for all supported platforms, so this is a size cost, not a reliability one.

## Migration Plan

Purely additive: a new CLI command, a new optional flag on an existing command (default off, so existing `merge` invocations are unaffected), and a new module. The only change to existing behavior is the new `pillow` entry in `pyproject.toml`'s `dependencies`, which affects fresh installs/upgrades but requires no action from existing users beyond `pip install -U pdfabric`. No data migration, no config migration, no rollback concerns beyond a normal version bump.
