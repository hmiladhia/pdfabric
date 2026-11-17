from __future__ import annotations

import io
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal, Optional, Union

from PIL import Image
from pypdf import PdfWriter
from pypdf._page import PageObject

StrPath = Union[str, Path]

CTM = tuple[
    tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]
]
ImageClass = Literal["bilevel", "alpha", "limited-palette", "photographic"]

_IDENTITY_CTM: CTM = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

DEFAULT_QUALITY = 80
DEFAULT_DPI = 150

RATIO_QUALITY_FLOOR = 20
RATIO_QUALITY_CEILING = 95
RATIO_MAX_ITERATIONS = 8
RATIO_TOLERANCE = 0.02


class CompressionRatioWarning(UserWarning):
    """Raised (as a warning) when ratio mode cannot reach its target."""


@dataclass
class _RatioResult:
    data: bytes
    achieved_ratio: float


def _multiply_ctm(first: CTM, second: CTM) -> CTM:
    return tuple(
        tuple(sum(first[row][k] * second[k][col] for k in range(3)) for col in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _classify_image(image: Image.Image) -> ImageClass:
    if image.mode == "1":
        return "bilevel"
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        return "alpha"
    if image.getcolors(maxcolors=256) is not None:
        return "limited-palette"
    return "photographic"


def _iter_image_placements(page: PageObject) -> Iterator[tuple[str, CTM]]:
    try:
        content = page.get_contents()
        resources = page.get("/Resources")
        xobjects = None
        if resources is not None:
            xobject_entry = resources.get_object().get("/XObject")
            if xobject_entry is not None:
                xobjects = xobject_entry.get_object()
    except Exception:
        return
    if content is None or not xobjects:
        return

    stack: list[CTM] = []
    ctm = _IDENTITY_CTM
    try:
        for operands, operator in content.operations:
            if operator == b"q":
                stack.append(ctm)
            elif operator == b"Q":
                if stack:
                    ctm = stack.pop()
            elif operator == b"cm":
                a, b, c, d, e, f = (float(value) for value in operands)
                ctm = _multiply_ctm(((a, b, 0.0), (c, d, 0.0), (e, f, 1.0)), ctm)
            elif operator == b"Do":
                name = str(operands[0])
                xobj = xobjects.get(name)
                if xobj is not None and xobj.get_object().get("/Subtype") == "/Image":
                    yield name, ctm
    except Exception:
        return


def _effective_dpi(ctm: CTM, width_px: int, height_px: int) -> Optional[float]:
    (a, b, _), (c, d, _), _ = ctm
    displayed_width = math.hypot(a, b)
    displayed_height = math.hypot(c, d)
    if displayed_width <= 0 or displayed_height <= 0:
        return None
    dpi_x = width_px / (displayed_width / 72)
    dpi_y = height_px / (displayed_height / 72)
    return max(dpi_x, dpi_y)


def _resize_for_dpi_cap(
    image: Image.Image, dpi_cap: Optional[int], effective_dpi: Optional[float]
) -> Image.Image:
    if dpi_cap is None or effective_dpi is None or effective_dpi <= dpi_cap:
        return image
    scale = dpi_cap / effective_dpi
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _compress_images(writer: PdfWriter, *, quality: int, dpi: Optional[int]) -> None:
    for page in writer.pages:
        placements = dict(_iter_image_placements(page))
        for key in page.images.keys():
            ctm = placements.get(key) if isinstance(key, str) else None
            image_file = page.images[key]
            pil_image = image_file.image
            if pil_image is None or _classify_image(pil_image) != "photographic":
                continue
            effective_dpi = (
                _effective_dpi(ctm, pil_image.width, pil_image.height)
                if ctm is not None
                else None
            )
            resized = _resize_for_dpi_cap(pil_image, dpi, effective_dpi)
            image_file.replace(resized, quality=quality)


def compress_writer(  # noqa: PLR0913 - each pass has its own independent flag
    writer: PdfWriter,
    *,
    quality: int = DEFAULT_QUALITY,
    dpi: Optional[int] = DEFAULT_DPI,
    images: bool = True,
    streams: bool = True,
    objects: bool = True,
) -> None:
    if images:
        _compress_images(writer, quality=quality, dpi=dpi)
    if streams:
        for page in writer.pages:
            page.compress_content_streams()
    if objects:
        writer.compress_identical_objects()


def _compress_bytes_to_ratio(
    original_bytes: bytes,
    ratio: float,
    *,
    images: bool = True,
    streams: bool = True,
    objects: bool = True,
) -> _RatioResult:
    original_size = len(original_bytes)
    low, high = RATIO_QUALITY_FLOOR, RATIO_QUALITY_CEILING
    best: Optional[_RatioResult] = None
    for _ in range(RATIO_MAX_ITERATIONS):
        if low > high:
            break
        quality = (low + high) // 2
        writer = PdfWriter(clone_from=io.BytesIO(original_bytes))
        compress_writer(
            writer,
            quality=quality,
            dpi=DEFAULT_DPI,
            images=images,
            streams=streams,
            objects=objects,
        )
        buffer = io.BytesIO()
        writer.write(buffer)
        data = buffer.getvalue()
        achieved_ratio = len(data) / original_size

        if best is None or abs(achieved_ratio - ratio) < abs(
            best.achieved_ratio - ratio
        ):
            best = _RatioResult(data=data, achieved_ratio=achieved_ratio)
        if abs(achieved_ratio - ratio) <= RATIO_TOLERANCE:
            break

        if achieved_ratio > ratio:
            high = quality - 1
        else:
            low = quality + 1

    assert best is not None  # noqa: S101 - RATIO_MAX_ITERATIONS is always >= 1
    return best


def compress_file(  # noqa: PLR0913 - mirrors the engine's independent pass/strength options
    input_path: StrPath,
    output: Optional[StrPath] = None,
    *,
    quality: Optional[int] = None,
    dpi: Optional[int] = None,
    ratio: Optional[float] = None,
    images: bool = True,
    streams: bool = True,
    objects: bool = True,
    force: bool = False,
) -> Path:
    if ratio is not None and (quality is not None or dpi is not None):
        raise ValueError("`ratio` cannot be combined with `quality` or `dpi`")

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output is not None:
        resolved_output = Path(output)
    else:
        resolved_output = input_path.with_name(f"{input_path.stem}.compressed.pdf")

    if resolved_output.exists() and not force:
        raise FileExistsError(f"Output file already exists: {resolved_output}")

    if ratio is not None:
        result = _compress_bytes_to_ratio(
            input_path.read_bytes(),
            ratio,
            images=images,
            streams=streams,
            objects=objects,
        )
        if abs(result.achieved_ratio - ratio) > RATIO_TOLERANCE:
            warnings.warn(
                f"Target ratio {ratio:.2f} was not reached; "
                f"achieved ratio is {result.achieved_ratio:.2f}",
                CompressionRatioWarning,
                stacklevel=2,
            )
        resolved_output.write_bytes(result.data)
        return resolved_output

    writer = PdfWriter(clone_from=input_path)
    compress_writer(
        writer,
        quality=DEFAULT_QUALITY if quality is None else quality,
        dpi=DEFAULT_DPI if dpi is None else dpi,
        images=images,
        streams=streams,
        objects=objects,
    )
    with resolved_output.open("wb") as stream:
        writer.write(stream)
    return resolved_output
