from __future__ import annotations

from typing import Optional

import click

from pdfabric.merge import merge_directory


@click.group()
def pdfabric() -> None:
    """pdfabric: PDF manipulation tools."""


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
def merge(
    directory: str,
    output: Optional[str],
    force: bool,
    add_bookmarks: bool,
) -> None:
    """Merge every top-level PDF in DIRECTORY into a single output PDF."""
    try:
        merge_directory(directory, output, force=force, add_bookmarks=add_bookmarks)
    except (FileNotFoundError, NotADirectoryError, ValueError, FileExistsError) as exc:
        raise click.ClickException(str(exc)) from exc


def main() -> None:
    pdfabric()


if __name__ == "__main__":
    main()
