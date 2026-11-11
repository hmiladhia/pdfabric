from pathlib import Path

from click.testing import CliRunner
from pypdf import PdfReader, PdfWriter

from pdfabric.cli import pdfabric


def _make_pdf(path: Path, num_pages: int) -> Path:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=100, height=200)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def test_merge_default_invocation(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)
    _make_pdf(source / "b.pdf", 2)

    result = CliRunner().invoke(pdfabric, ["merge", str(source)])

    assert result.exit_code == 0, result.output
    output = tmp_path / "docs.pdf"
    assert output.exists()
    reader = PdfReader(output)
    expected_page_count = 3
    expected_bookmark_count = 2
    assert len(reader.pages) == expected_page_count
    assert len(reader.outline) == expected_bookmark_count


def test_merge_explicit_output(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)
    output = tmp_path / "custom.pdf"

    result = CliRunner().invoke(pdfabric, ["merge", str(source), "-o", str(output)])

    assert result.exit_code == 0, result.output
    assert output.exists()


def test_merge_force_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)
    output = tmp_path / "out.pdf"
    output.write_bytes(b"existing")

    result = CliRunner().invoke(
        pdfabric, ["merge", str(source), "-o", str(output), "-f"]
    )

    assert result.exit_code == 0, result.output
    assert len(PdfReader(output).pages) == 1


def test_merge_no_bookmarks(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)
    output = tmp_path / "out.pdf"

    result = CliRunner().invoke(
        pdfabric, ["merge", str(source), "-o", str(output), "--no-bookmarks"]
    )

    assert result.exit_code == 0, result.output
    assert PdfReader(output).outline == []


def test_merge_missing_directory_errors_cleanly(tmp_path: Path) -> None:
    result = CliRunner().invoke(pdfabric, ["merge", str(tmp_path / "missing")])

    assert result.exit_code != 0
    assert "Traceback" not in result.output


def test_merge_empty_directory_errors_cleanly(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()

    result = CliRunner().invoke(pdfabric, ["merge", str(source)])

    assert result.exit_code != 0
    assert "Traceback" not in result.output


def test_merge_existing_output_without_force_errors_cleanly(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    _make_pdf(source / "a.pdf", 1)
    output = tmp_path / "out.pdf"
    output.write_bytes(b"existing")

    result = CliRunner().invoke(pdfabric, ["merge", str(source), "-o", str(output)])

    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert output.read_bytes() == b"existing"
