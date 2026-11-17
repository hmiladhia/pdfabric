# PDF Compress Specification

## Purpose

Shrinking a PDF's file size by recompressing its images, deflating content streams, and deduplicating identical objects, with safeguards that prevent lossy image recompression from degrading non-photographic content - available as both a Python library call and a `pdfabric compress` CLI command.

## Requirements

### Requirement: Three independently toggleable compression passes
The system SHALL compress a PDF through three independently toggleable passes - image recompression, content-stream deflation, and duplicate-object deduplication - each enabled by default.

#### Scenario: All passes run by default
- **WHEN** a PDF is compressed with no passes explicitly disabled
- **THEN** images are recompressed (subject to classification), content streams are deflated, and identical objects are deduplicated

#### Scenario: A pass can be disabled independently
- **WHEN** a PDF is compressed with the image pass disabled, the stream pass disabled, or the object pass disabled
- **THEN** only the remaining enabled passes run, and the disabled pass makes no change of its kind to the output

### Requirement: Per-image classification before lossy recompression
Before attempting lossy recompression of any image, the system SHALL classify the image and SHALL skip lossy recompression for an image that is bilevel, has an alpha channel, or uses a limited color palette characteristic of line art or screenshots. Only images classified as photographic SHALL be lossily recompressed.

#### Scenario: Photographic image is recompressed
- **WHEN** the image pass runs on an image with a continuous-tone, many-color RGB or grayscale body
- **THEN** that image is recompressed as JPEG at the effective quality for the run

#### Scenario: Bilevel image is left untouched by lossy recompression
- **WHEN** the image pass runs on a 1-bit (bilevel) image
- **THEN** that image is not recompressed as JPEG

#### Scenario: Image with an alpha channel is left untouched by lossy recompression
- **WHEN** the image pass runs on an image that has an alpha/transparency channel
- **THEN** that image is not recompressed as JPEG, and its transparency is preserved

#### Scenario: Limited-palette image is left untouched by lossy recompression
- **WHEN** the image pass runs on an image with a small, limited color palette characteristic of line art or a screenshot
- **THEN** that image is not recompressed as JPEG

### Requirement: Direct quality and DPI control
The system SHALL accept a direct JPEG quality (0-100) and/or a DPI cap as controls for the image pass: quality sets the re-encoding quality for images classified as photographic, and the DPI cap downsamples an image whose effective on-page DPI exceeds it, down to that cap.

#### Scenario: Quality controls JPEG re-encoding
- **WHEN** a quality value is given and the image pass runs on a photographic image
- **THEN** that image is re-encoded as JPEG at the given quality

#### Scenario: DPI cap downsamples an oversized image
- **WHEN** a DPI cap is given and an image's effective on-page DPI exceeds that cap
- **THEN** the image is downsampled so its effective on-page DPI no longer exceeds the cap

#### Scenario: Image under the DPI cap is not downsampled
- **WHEN** a DPI cap is given and an image's effective on-page DPI is already at or below that cap
- **THEN** the image's pixel dimensions are not changed by the DPI cap

#### Scenario: Effective DPI cannot be determined for an image
- **WHEN** the DPI cap is given but the image's placement transformation on the page cannot be determined
- **THEN** that image is not downsampled, the image pass still applies quality-based recompression to it if it is classified as photographic, and the run does not fail because of this image

#### Scenario: No strength option given
- **WHEN** a PDF is compressed with neither a target ratio nor an explicit quality or DPI cap given
- **THEN** the system applies a default quality of 80 and a default DPI cap of 150 to the image pass

### Requirement: Target-ratio control
The system SHALL accept a target ratio, expressed as a fraction between 0 and 1 of the original file size, as an alternative to direct quality/DPI control. The system SHALL search for a quality that brings the output close to that target, bounded by a minimum quality floor, and SHALL NOT be given together with an explicit quality or DPI cap.

#### Scenario: Ratio search converges near the target
- **WHEN** a target ratio is given for a PDF whose images can be compressed enough to reach it without the search quality dropping below the floor
- **THEN** the output file size is close to the target ratio of the original size

#### Scenario: Target ratio is unreachable above the quality floor
- **WHEN** a target ratio is given but it cannot be reached without the search quality dropping below the floor (for example, a PDF with little compressible image content)
- **THEN** the system writes the output at the quality floor instead of failing, and reports that the achieved ratio did not reach the requested target

#### Scenario: Ratio and direct quality/DPI are mutually exclusive
- **WHEN** a target ratio is given together with an explicit quality or DPI cap
- **THEN** the operation fails with an error identifying that the two controls cannot be combined, and no output file is written

### Requirement: Default output location and overwrite protection
When no explicit output path is given, the system SHALL write the compressed PDF as a sibling of the input file. The system SHALL refuse to overwrite an existing output file unless the caller explicitly requests it.

#### Scenario: Default output path derived from input name
- **WHEN** compressing `/docs/report.pdf` with no explicit output path
- **THEN** the output is written to `/docs/report.compressed.pdf`

#### Scenario: Existing output blocks compression by default
- **WHEN** the resolved output path already exists and the caller has not requested a forced overwrite
- **THEN** the operation fails with an error identifying that the output already exists, and the existing file is left unmodified

#### Scenario: Forced overwrite replaces existing output
- **WHEN** the resolved output path already exists and the caller has requested a forced overwrite
- **THEN** the existing file is replaced with the newly compressed PDF

### Requirement: CLI command for PDF compression
The system SHALL expose the compression capability as a `pdfabric compress INPUT` command, with options controlling output path, overwrite, pass selection, and compression strength.

#### Scenario: Default invocation
- **WHEN** a user runs `pdfabric compress INPUT` with no other options
- **THEN** the command runs all three passes with the default quality and DPI cap, writing to the default output path, failing without overwriting if that output already exists

#### Scenario: Explicit output path
- **WHEN** a user runs `pdfabric compress INPUT -o/--output PATH`
- **THEN** the compressed PDF is written to `PATH` instead of the default location

#### Scenario: Forced overwrite via CLI
- **WHEN** a user runs `pdfabric compress INPUT -f/--force` and the output path already exists
- **THEN** the existing file is overwritten instead of the command failing

#### Scenario: Strength and pass options via CLI
- **WHEN** a user runs `pdfabric compress INPUT` with `--ratio`, or with `--quality`/`--dpi`, and/or with any of `--images/--no-images`, `--streams/--no-streams`, `--objects/--no-objects`
- **THEN** the command applies those options as described by the corresponding requirements above

#### Scenario: Command reports errors clearly and exits non-zero
- **WHEN** the underlying compression fails for any reason (invalid input, existing output without `--force`, `--ratio` combined with `--quality`/`--dpi`)
- **THEN** the CLI prints a clear, user-facing error message and exits with a non-zero status, without a Python traceback
