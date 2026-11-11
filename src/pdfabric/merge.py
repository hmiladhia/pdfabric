from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Union

from pypdf import PdfWriter

StrPath = Union[str, Path]


def _format_bookmark_title(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").title()


def merge_files(
    paths: Iterable[StrPath],
    output: StrPath,
    *,
    force: bool = False,
    add_bookmarks: bool = True,
) -> None:
    output = Path(output)
    if output.exists() and not force:
        raise FileExistsError(f"Output file already exists: {output}")

    writer = PdfWriter()
    for raw_path in paths:
        path = Path(raw_path)
        first_page = len(writer.pages)
        writer.append(path)
        if add_bookmarks:
            writer.add_outline_item(_format_bookmark_title(path.stem), first_page)

    with output.open("wb") as stream:
        writer.write(stream)


def merge_directory(
    directory: StrPath,
    output: Optional[StrPath] = None,
    *,
    force: bool = False,
    add_bookmarks: bool = True,
) -> Path:
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    pdf_files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    if not pdf_files:
        raise ValueError(f"No PDF files found in directory: {directory}")

    if output is not None:
        resolved_output = Path(output)
    else:
        resolved_output = directory.parent / f"{directory.name}.pdf"

    merge_files(pdf_files, resolved_output, force=force, add_bookmarks=add_bookmarks)
    return resolved_output
