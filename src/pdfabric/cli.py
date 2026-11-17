from __future__ import annotations

import warnings
from typing import Optional

import click

from pdfabric.compress import CompressionRatioWarning, compress_file
from pdfabric.merge import merge_directory


@click.group()
def pdfabric() -> None:
    """pdfabric: PDF manipulation tools."""


def _echo_ratio_warnings(caught: list[warnings.WarningMessage]) -> None:
    for warning in caught:
        if issubclass(warning.category, CompressionRatioWarning):
            click.echo(f"Warning: {warning.message}")


@pdfabric.command()
@click.argument("directory", type=click.Path())
@click.option(
    "-o",
    "--output",
    "output",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to a sibling of DIRECTORY named after it.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the output file if it already exists.",
)
@click.option(
    "--bookmarks/--no-bookmarks",
    "add_bookmarks",
    default=True,
    help="Add a bookmark per source file to the merged output.",
)
@click.option(
    "--compress",
    "compress_ratio",
    type=click.FloatRange(0, 1),
    default=None,
    help="Compress the merged output to approximately this fraction of its size.",
)
def merge(
    directory: str,
    output: Optional[str],
    force: bool,
    add_bookmarks: bool,
    compress_ratio: Optional[float],
) -> None:
    """Merge every top-level PDF in DIRECTORY into a single output PDF."""
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", CompressionRatioWarning)
            merge_directory(
                directory,
                output,
                force=force,
                add_bookmarks=add_bookmarks,
                compress=compress_ratio,
            )
        _echo_ratio_warnings(caught)
    except (FileNotFoundError, NotADirectoryError, ValueError, FileExistsError) as exc:
        raise click.ClickException(str(exc)) from exc


@pdfabric.command()
@click.argument("input_path", type=click.Path(), metavar="INPUT")
@click.option(
    "-o",
    "--output",
    "output",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to a sibling of INPUT named '<stem>.compressed.pdf'.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the output file if it already exists.",
)
@click.option(
    "--quality",
    type=click.IntRange(0, 100),
    default=None,
    help="JPEG quality for recompressed photographic images. Default: 80.",
)
@click.option(
    "--dpi",
    type=click.IntRange(min=1),
    default=None,
    help="Downsample images whose effective on-page DPI exceeds this cap. Default: 150.",
)
@click.option(
    "--ratio",
    type=click.FloatRange(0, 1),
    default=None,
    help="Target output size as a fraction of the input size. Cannot be combined with "
    "--quality/--dpi.",
)
@click.option(
    "--images/--no-images",
    "images",
    default=True,
    help="Enable (default) or disable the image recompression pass.",
)
@click.option(
    "--streams/--no-streams",
    "streams",
    default=True,
    help="Enable (default) or disable the content-stream deflation pass.",
)
@click.option(
    "--objects/--no-objects",
    "objects",
    default=True,
    help="Enable (default) or disable the identical-object deduplication pass.",
)
def compress(  # noqa: PLR0913 - one parameter per CLI option
    input_path: str,
    output: Optional[str],
    force: bool,
    quality: Optional[int],
    dpi: Optional[int],
    ratio: Optional[float],
    images: bool,
    streams: bool,
    objects: bool,
) -> None:
    """Compress INPUT, shrinking its file size."""
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", CompressionRatioWarning)
            compress_file(
                input_path,
                output,
                quality=quality,
                dpi=dpi,
                ratio=ratio,
                images=images,
                streams=streams,
                objects=objects,
                force=force,
            )
        _echo_ratio_warnings(caught)
    except (FileNotFoundError, ValueError, FileExistsError) as exc:
        raise click.ClickException(str(exc)) from exc


def main() -> None:
    pdfabric()


if __name__ == "__main__":
    main()
