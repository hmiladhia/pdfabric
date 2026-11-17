from __future__ import annotations

import io
import random
import warnings
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from pdfabric.compress import (
    CompressionRatioWarning,
    DEFAULT_DPI,
    _classify_image,
    _compress_bytes_to_ratio,
    _effective_dpi,
    _iter_image_placements,
    compress_file,
    compress_writer,
)


def _solid_image(mode: str, size: tuple[int, int] = (20, 20)) -> Image.Image:
    if mode == "P":
        image = Image.new("P", size)
        image.putpalette([i for i in range(256) for _ in range(3)][:768])
        return image
    if mode == "RGBA":
        return Image.new("RGBA", size, (255, 0, 0, 128))
    return Image.new(mode, size)


def _random_photo(size: tuple[int, int] = (64, 64), seed: int = 0) -> Image.Image:
    rng = random.Random(seed)  # noqa: S311 - test fixture pixel data, not security-sensitive
    image = Image.new("RGB", size)
    pixel_count = size[0] * size[1]
    pixels = [
        (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
        for _ in range(pixel_count)
    ]
    image.putdata(pixels)
    return image


def _embed_as_pdf(
    image: Image.Image, dpi: int = 150, **save_kwargs: object
) -> PdfWriter:
    buffer = io.BytesIO()
    image.save(buffer, "PDF", dpi=(dpi, dpi), **save_kwargs)
    buffer.seek(0)
    writer = PdfWriter()
    writer.append(buffer)
    return writer


def _write_pdf(writer: PdfWriter, path: Path) -> Path:
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def _build_page_with_dummy_image(
    content_bytes: bytes, width: int = 100, height: int = 100
) -> PageObject:
    page = PageObject.create_blank_page(pdf=None, width=width, height=height)
    stream = DecodedStreamObject()
    stream.set_data(content_bytes)
    page[NameObject("/Contents")] = stream

    image_xobj = DictionaryObject()
    image_xobj[NameObject("/Subtype")] = NameObject("/Image")
    image_xobj[NameObject("/Width")] = NumberObject(width)
    image_xobj[NameObject("/Height")] = NumberObject(height)
    xobjects = DictionaryObject()
    xobjects[NameObject("/image")] = image_xobj
    resources = DictionaryObject()
    resources[NameObject("/XObject")] = xobjects
    page[NameObject("/Resources")] = resources
    return page


# -- 2.1 Image classification --------------------------------------------------


def test_classify_bilevel_image() -> None:
    assert _classify_image(_solid_image("1")) == "bilevel"


def test_classify_alpha_image() -> None:
    assert _classify_image(_solid_image("RGBA")) == "alpha"


def test_classify_limited_palette_image() -> None:
    assert _classify_image(_solid_image("P")) == "limited-palette"


def test_classify_photographic_image() -> None:
    assert _classify_image(_random_photo()) == "photographic"


# -- 3.1 Content-stream CTM walk ------------------------------------------------


def test_iter_image_placements_untransformed() -> None:
    page = _build_page_with_dummy_image(b"/image Do")

    placements = list(_iter_image_placements(page))

    assert len(placements) == 1
    name, ctm = placements[0]
    assert name == "/image"
    assert ctm == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def test_iter_image_placements_scaled() -> None:
    page = _build_page_with_dummy_image(b"q 2 0 0 2 0 0 cm /image Do Q")

    placements = list(_iter_image_placements(page))

    assert len(placements) == 1
    name, ctm = placements[0]
    assert name == "/image"
    assert ctm == ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 1.0))


def test_iter_image_placements_nested_q_pair() -> None:
    page = _build_page_with_dummy_image(
        b"q 2 0 0 2 0 0 cm q 3 0 0 3 0 0 cm /image Do Q Q"
    )

    placements = list(_iter_image_placements(page))

    assert len(placements) == 1
    name, ctm = placements[0]
    assert name == "/image"
    # inner scale (3) composed with outer scale (2) => combined scale of 6
    assert ctm == ((6.0, 0.0, 0.0), (0.0, 6.0, 0.0), (0.0, 0.0, 1.0))


# -- 3.2 Effective DPI computation ----------------------------------------------


def test_effective_dpi_known_placement() -> None:
    # A 100x100px image placed in a 1in x 1in (72x72pt) box is 100 DPI.
    ctm = ((72.0, 0.0, 0.0), (0.0, 72.0, 0.0), (0.0, 0.0, 1.0))

    assert _effective_dpi(ctm, 100, 100) == pytest.approx(100.0)


# -- 3.3 Graceful fallback on malformed content streams -------------------------


def test_iter_image_placements_malformed_stream_does_not_raise() -> None:
    page = _build_page_with_dummy_image(
        b"q 1 2 cm /image Do Q"
    )  # malformed `cm` operand count

    placements = list(_iter_image_placements(page))

    assert placements == []


# -- 4.1/4.2/4.3 Image pass ------------------------------------------------------


def test_image_pass_recompresses_photographic_image(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "photo.pdf")
    high_quality_size = PdfReader(path).pages[0].images[0].data.__len__()

    writer = PdfWriter(clone_from=path)
    compress_writer(writer, quality=20, dpi=150)
    low_quality_data = writer.pages[0].images[0].data

    assert len(low_quality_data) < high_quality_size


@pytest.mark.parametrize("mode", ["1", "P", "RGBA"])
def test_image_pass_leaves_non_photographic_images_untouched(mode: str) -> None:
    writer = _embed_as_pdf(_solid_image(mode))
    before = writer.pages[0].images[0].data

    compress_writer(writer, quality=20, dpi=150)

    after = writer.pages[0].images[0].data
    assert after == before


def test_image_pass_downsamples_oversized_image() -> None:
    writer = _embed_as_pdf(_random_photo((300, 300)), dpi=300)

    compress_writer(writer, quality=80, dpi=150)

    assert writer.pages[0].images[0].image.size == (150, 150)


def test_image_pass_keeps_dimensions_under_cap() -> None:
    writer = _embed_as_pdf(_random_photo((100, 100)), dpi=72)

    compress_writer(writer, quality=80, dpi=150)

    assert writer.pages[0].images[0].image.size == (100, 100)


def test_default_quality_and_dpi_applied(tmp_path: Path) -> None:
    # An image placed at twice the default DPI cap should be downsampled by
    # half when compress_file is given no explicit quality/dpi.
    source_dpi = DEFAULT_DPI * 2
    writer = _embed_as_pdf(_random_photo((source_dpi, source_dpi)), dpi=source_dpi)
    path = _write_pdf(writer, tmp_path / "photo.pdf")

    output = compress_file(path)

    result_image = PdfReader(output).pages[0].images[0].image
    assert result_image.size == (DEFAULT_DPI, DEFAULT_DPI)


# -- 5.1/5.2/5.3 Writer-level engine and compress_file ---------------------------


def test_compress_writer_runs_directly_on_writer() -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)

    compress_writer(writer, quality=20, dpi=150)

    assert writer.pages[0].images[0].image is not None


def test_compress_file_default_output_path(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "report.pdf")

    output = compress_file(path)

    assert output == tmp_path / "report.compressed.pdf"
    assert output.exists()


def test_compress_file_raises_if_output_exists(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "report.pdf")
    output = tmp_path / "out.pdf"
    output.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        compress_file(path, output=output)

    assert output.read_bytes() == b"existing"


def test_compress_file_force_overwrites_existing(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "report.pdf")
    output = tmp_path / "out.pdf"
    output.write_bytes(b"existing")

    compress_file(path, output=output, force=True)

    assert len(PdfReader(output).pages) == 1


def test_compress_file_raises_for_missing_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compress_file(tmp_path / "missing.pdf")


def test_images_flag_independently_controls_image_pass(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "report.pdf")

    with_images = compress_file(
        path, output=tmp_path / "with.pdf", quality=20, streams=False, objects=False
    )
    without_images = compress_file(
        path,
        output=tmp_path / "without.pdf",
        quality=20,
        images=False,
        streams=False,
        objects=False,
    )

    assert with_images.read_bytes() != without_images.read_bytes()
    with_image_data = PdfReader(with_images).pages[0].images[0].data
    without_image_data = PdfReader(without_images).pages[0].images[0].data
    assert with_image_data != without_image_data


def test_streams_flag_independently_controls_stream_pass(tmp_path: Path) -> None:
    # A content stream with many repeated operators compresses well with FlateDecode.
    content = b" ".join([b"1 0 0 1 0 0 cm"] * 500)
    page = _build_page_with_dummy_image(content)
    writer = PdfWriter()
    writer.add_page(page)
    path = _write_pdf(writer, tmp_path / "report.pdf")

    with_streams = compress_file(
        path, output=tmp_path / "with.pdf", images=False, objects=False
    )
    without_streams = compress_file(
        path,
        output=tmp_path / "without.pdf",
        images=False,
        streams=False,
        objects=False,
    )

    assert with_streams.stat().st_size < without_streams.stat().st_size


def test_objects_flag_independently_controls_object_pass(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    source = tmp_path / "source.pdf"
    _write_pdf(writer, source)

    combined = PdfWriter()
    combined.append(source)
    combined.append(source)  # duplicate page/object graph
    path = tmp_path / "duplicated.pdf"
    _write_pdf(combined, path)

    with_objects = compress_file(
        path, output=tmp_path / "with.pdf", images=False, streams=False
    )
    without_objects = compress_file(
        path,
        output=tmp_path / "without.pdf",
        images=False,
        streams=False,
        objects=False,
    )

    assert with_objects.stat().st_size < without_objects.stat().st_size


# -- 6.1/6.2/6.3 Ratio mode -------------------------------------------------------


def test_ratio_mode_converges_near_target() -> None:
    original = _embed_as_pdf(_random_photo((400, 400)), dpi=300)
    buffer = io.BytesIO()
    original.write(buffer)
    original_bytes = buffer.getvalue()

    # Empirically, quality 20-95 at the fixed default DPI cap spans achieved
    # ratios of roughly 0.05-0.37 for this fixture, so 0.2 is reachable
    # without hitting the quality floor.
    target_ratio = 0.2
    search_tolerance = 0.05
    result = _compress_bytes_to_ratio(original_bytes, target_ratio)

    assert abs(result.achieved_ratio - target_ratio) <= search_tolerance


def test_ratio_mode_unreachable_target_still_writes_best_effort(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "report.pdf")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", CompressionRatioWarning)
        output = compress_file(path, ratio=0.0001)

    assert output.exists()
    assert any(issubclass(w.category, CompressionRatioWarning) for w in caught)


def test_ratio_combined_with_quality_raises_value_error(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "report.pdf")
    output = tmp_path / "out.pdf"

    with pytest.raises(ValueError, match="ratio"):
        compress_file(path, output=output, ratio=0.5, quality=50)

    assert not output.exists()


def test_ratio_combined_with_dpi_raises_value_error(tmp_path: Path) -> None:
    writer = _embed_as_pdf(_random_photo(), dpi=150)
    path = _write_pdf(writer, tmp_path / "report.pdf")
    output = tmp_path / "out.pdf"

    with pytest.raises(ValueError, match="ratio"):
        compress_file(path, output=output, ratio=0.5, dpi=100)

    assert not output.exists()
