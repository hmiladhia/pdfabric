from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pdfabric.merge import _format_bookmark_title, merge_directory, merge_files


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("invoice_report_2024", "Invoice Report 2024"),
        ("01-cover-letter", "01 Cover Letter"),
        ("Report", "Report"),
    ],
)
def test_format_bookmark_title(stem: str, expected: str) -> None:
    assert _format_bookmark_title(stem) == expected


def _make_pdf(path: Path, num_pages: int, width: int = 100) -> Path:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=width, height=200)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def test_merge_files_page_ordering(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2, width=100)
    b = _make_pdf(tmp_path / "b.pdf", 3, width=200)
    output = tmp_path / "merged.pdf"

    merge_files([a, b], output)

    reader = PdfReader(output)
    expected_page_count = 5
    assert len(reader.pages) == expected_page_count
    widths = [int(page.mediabox.width) for page in reader.pages]
    assert widths == [100, 100, 200, 200, 200]


def test_merge_files_adds_bookmarks_by_default(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "invoice_one.pdf", 1)
    b = _make_pdf(tmp_path / "invoice-two.pdf", 2)
    output = tmp_path / "merged.pdf"

    merge_files([a, b], output)

    reader = PdfReader(output)
    titles = [item.title for item in reader.outline]
    assert titles == ["Invoice One", "Invoice Two"]


def test_merge_files_no_bookmarks_when_disabled(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 1)
    output = tmp_path / "merged.pdf"

    merge_files([a], output, add_bookmarks=False)

    reader = PdfReader(output)
    assert reader.outline == []


def test_merge_files_raises_if_output_exists(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 1)
    output = tmp_path / "merged.pdf"
    output.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        merge_files([a], output)

    assert output.read_bytes() == b"existing"


def test_merge_files_force_overwrites_existing(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 1)
    output = tmp_path / "merged.pdf"
    output.write_bytes(b"existing")

    merge_files([a], output, force=True)

    reader = PdfReader(output)
    assert len(reader.pages) == 1


def test_merge_directory_alphabetical_order(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "b.pdf", 1, width=100)
    _make_pdf(source / "a.pdf", 1, width=200)
    _make_pdf(source / "c.pdf", 1, width=300)
    output = tmp_path / "out.pdf"

    merge_directory(source, output, add_bookmarks=False)

    reader = PdfReader(output)
    widths = [int(page.mediabox.width) for page in reader.pages]
    assert widths == [200, 100, 300]


def test_merge_directory_ignores_non_pdf_files(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)
    (source / "notes.txt").write_text("not a pdf")
    (source / "report.docx").write_bytes(b"not a pdf")
    output = tmp_path / "out.pdf"

    merge_directory(source, output)

    reader = PdfReader(output)
    assert len(reader.pages) == 1


def test_merge_directory_ignores_subdirectories(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)
    nested = source / "nested"
    nested.mkdir()
    _make_pdf(nested / "b.pdf", 1)
    output = tmp_path / "out.pdf"

    merge_directory(source, output)

    reader = PdfReader(output)
    assert len(reader.pages) == 1


def test_merge_directory_raises_when_empty(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()

    with pytest.raises(ValueError, match="No PDF files found"):
        merge_directory(source, tmp_path / "out.pdf")


def test_merge_directory_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        merge_directory(tmp_path / "missing", tmp_path / "out.pdf")


def test_merge_directory_raises_when_not_a_directory(tmp_path: Path) -> None:
    not_a_dir = tmp_path / "a.pdf"
    _make_pdf(not_a_dir, 1)

    with pytest.raises(NotADirectoryError):
        merge_directory(not_a_dir, tmp_path / "out.pdf")


def test_merge_directory_default_output_path(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)

    resolved = merge_directory(source)

    assert resolved == tmp_path / "docs.pdf"
    assert resolved.exists()
