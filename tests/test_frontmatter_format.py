from pathlib import Path

import pytest

from frontmatter_format.frontmatter_format import (
    FmFormatError,
    FmStyle,
    fmf_insert_frontmatter,
    fmf_read,
    fmf_read_frontmatter,
    fmf_read_frontmatter_raw,
    fmf_strip_frontmatter,
    fmf_write,
)
from frontmatter_format.key_sort import custom_key_sort
from frontmatter_format.yaml_util import dump_yaml


def test_fmf_basic(tmp_path: Path):
    # Test with Markdown.
    file_path_md = tmp_path / "test_write.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_md, content_md, metadata_md)
    lines = file_path_md.read_text().splitlines(keepends=True)
    assert lines[0] == FmStyle.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading Markdown.
    file_path_md = tmp_path / "test_read.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_md, "w") as f:
        f.write(FmStyle.yaml.start + "\n")
        f.write("title: Test Title\n")
        f.write("author: Test Author\n")
        f.write(FmStyle.yaml.end + "\n")
        f.write(content_md)
    read_content_md, read_metadata_md = fmf_read(file_path_md)
    assert read_content_md.strip() == content_md
    assert read_metadata_md == metadata_md

    # Test with HTML.
    file_path_html = tmp_path / "test_write.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_html, content_html, metadata_html, style=FmStyle.html)
    lines = file_path_html.read_text().splitlines(keepends=True)
    assert lines[0] == FmStyle.html.start + "\n"
    assert lines[-1].strip() == content_html
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading HTML.
    file_path_html = tmp_path / "test_read.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_html, "w") as f:
        f.write(FmStyle.html.start + "\n")
        dump_yaml(metadata_html, f)
        f.write(FmStyle.html.end + "\n")
        f.write(content_html)
    read_content_html, read_metadata_html = fmf_read(file_path_html)
    assert read_content_html.strip() == content_html
    assert read_metadata_html == metadata_html

    # Test with code frontmatter.
    file_path_code = tmp_path / "test_write_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_code, content_code, metadata_code, style=FmStyle.hash)
    lines = file_path_code.read_text().splitlines(keepends=True)
    assert lines[0] == FmStyle.hash.start + "\n"
    assert lines[-1].strip() == content_code
    assert "# title: Test Title\n" in lines
    assert "# author: Test Author\n" in lines

    # Test reading code frontmatter.
    file_path_code = tmp_path / "test_read_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_code, "w") as f:
        f.write(FmStyle.hash.start + "\n")
        f.write("# title: Test Title\n")
        f.write("# author: Test Author\n")
        f.write(FmStyle.hash.end + "\n")
        f.write(content_code)
    read_content_code, read_metadata_code = fmf_read(file_path_code)
    assert read_content_code.strip() == content_code
    assert read_metadata_code == metadata_code


def test_fmf_slash_style(tmp_path: Path):
    """Test write/read round-trip for slash (Rust/C++) style frontmatter."""
    file_path = tmp_path / "test.rs"
    content = "fn main() {}"
    metadata = {"title": "Test Title", "author": "Test Author"}

    fmf_write(file_path, content, metadata, style=FmStyle.slash)
    lines = file_path.read_text().splitlines(keepends=True)
    assert lines[0] == "//---\n"
    assert "// title: Test Title\n" in lines
    assert "// author: Test Author\n" in lines

    read_content, read_metadata = fmf_read(file_path)
    assert read_content.strip() == content
    assert read_metadata == metadata


def test_fmf_slash_star_style(tmp_path: Path):
    """Test write/read round-trip for slash-star (CSS/JS/C) style frontmatter."""
    file_path = tmp_path / "test.css"
    content = ".hello { color: green; }"
    metadata = {"title": "Test Title", "author": "Test Author"}

    fmf_write(file_path, content, metadata, style=FmStyle.slash_star)
    lines = file_path.read_text().splitlines(keepends=True)
    assert lines[0] == "/*---\n"
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    read_content, read_metadata = fmf_read(file_path)
    assert read_content.strip() == content
    assert read_metadata == metadata


def test_fmf_dash_style(tmp_path: Path):
    """Test write/read round-trip for dash (SQL) style frontmatter."""
    file_path = tmp_path / "test.sql"
    content = "SELECT * FROM world;"
    metadata = {"title": "Test Title", "author": "Test Author"}

    fmf_write(file_path, content, metadata, style=FmStyle.dash)
    lines = file_path.read_text().splitlines(keepends=True)
    assert lines[0] == "----\n"
    assert "-- title: Test Title\n" in lines
    assert "-- author: Test Author\n" in lines

    read_content, read_metadata = fmf_read(file_path)
    assert read_content.strip() == content
    assert read_metadata == metadata


def test_fmf_five_dashes_is_not_frontmatter(tmp_path: Path):
    """Test that five dashes are not recognized as a valid frontmatter delimiter."""
    file_path = tmp_path / "five_dashes.md"
    file_text = "-----\nhello\n"
    file_path.write_text(file_text)

    raw, content_offset, metadata_start_offset = fmf_read_frontmatter_raw(file_path)
    assert raw is None
    assert content_offset == 0
    assert metadata_start_offset == 0

    read_content, read_metadata = fmf_read(file_path)
    assert read_content == file_text
    assert read_metadata is None


def test_fmf_with_custom_key_sort(tmp_path: Path):
    # Test with Markdown.
    file_path_md = tmp_path / "test_write_custom_sort.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author", "date": "2022-01-01"}
    fmf_write(file_path_md, content_md, metadata_md, key_sort=custom_key_sort(["date", "title"]))
    lines = file_path_md.read_text().splitlines(keepends=True)
    assert lines[0] == FmStyle.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    # Check that the priority keys come first in the order they are in the list
    assert lines[1].strip() == "date: '2022-01-01'"
    assert lines[2].strip() == "title: Test Title"
    assert lines[3].strip() == "author: Test Author"


def test_fmf_metadata(tmp_path: Path):
    # Test offsets.
    file_path = tmp_path / "test_offset.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path, content, metadata)
    result, content_offset, metadata_start_offset = fmf_read_frontmatter_raw(file_path)
    assert result == """title: Test Title\nauthor: Test Author\n"""
    assert content_offset == len(result) + 2 * (len("---") + 1)
    assert metadata_start_offset == 0  # Metadata starts at beginning of file

    # Test a zero-length file.
    zero_length_file = tmp_path / "empty_file.txt"
    zero_length_file.touch()

    result, content_offset, metadata_start_offset = fmf_read_frontmatter_raw(zero_length_file)
    assert (result, content_offset, metadata_start_offset) == (None, 0, 0)

    # Test stripping metadata from Markdown.
    file_path = tmp_path / "test_strip_metadata.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path, content, metadata)
    fmf_strip_frontmatter(file_path)
    stripped_content = file_path.read_text()
    assert stripped_content.strip() == content

    # Test inserting metadata into a file without frontmatter.
    file_path = tmp_path / "test_insert_no_frontmatter.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    file_path.write_text(content)
    fmf_insert_frontmatter(file_path, metadata)
    new_content, new_metadata = fmf_read(file_path)
    assert new_metadata == metadata
    assert new_content == content
    # Overwrite the existing metadata.
    metadata2 = {"something": "else"}
    fmf_insert_frontmatter(file_path, metadata2)
    new_content, new_metadata = fmf_read(file_path)
    assert new_metadata == metadata2
    assert new_content == content


def test_hash_style_with_initial_hash_lines(tmp_path: Path):
    """Test that hash style files can have arbitrary # lines before the frontmatter."""
    content = "print('Hello, World!')"
    metadata = {"title": "Test Title", "author": "Test Author"}

    # Test with a shebang line before the frontmatter
    file_path = tmp_path / "test_hash_with_shebang.py"
    with open(file_path, "w") as f:
        f.write("#!/usr/bin/env python\n")
        f.write("# Python inline script metadata\n")
        f.write("#---\n")
        f.write("# title: Test Title\n")
        f.write("# author: Test Author\n")
        f.write("#---\n")
        f.write(content)

    # Read and verify the metadata
    read_content, read_metadata = fmf_read(file_path)
    assert read_content.strip() == content
    assert read_metadata == metadata

    # Test with multiple # lines and comments before the frontmatter
    file_path = tmp_path / "test_hash_with_multiple_comments.py"
    with open(file_path, "w") as f:
        f.write("#!/usr/bin/env python\n")
        f.write("# Copyright 2025\n")
        f.write("# This is a sample file\n")
        f.write("#---\n")
        f.write("# title: Test Title\n")
        f.write("# author: Test Author\n")
        f.write("#---\n")
        f.write(content)

    # Read and verify the metadata
    read_content, read_metadata = fmf_read(file_path)
    assert read_content.strip() == content
    assert read_metadata == metadata

    # Specifically check that metadata_start_offset is positioned at the #--- line
    raw_metadata, content_offset, metadata_start_offset = fmf_read_frontmatter_raw(file_path)
    assert raw_metadata == "title: Test Title\nauthor: Test Author\n"

    # Verify the metadata_start_offset is accurate by reading those bytes
    with open(file_path, "rb") as f:
        f.seek(metadata_start_offset)
        start_line = f.readline().decode("utf-8").strip()
        assert start_line == "#---"  # The start delimiter

    # Test that non-# lines before #--- are not accepted as hash style
    file_path = tmp_path / "test_hash_with_non_hash_lines.py"
    with open(file_path, "w") as f:
        f.write("#!/usr/bin/env python\n")
        f.write("import sys  # This is not a comment line\n")
        f.write("#---\n")
        f.write("# title: Test Title\n")
        f.write("# author: Test Author\n")
        f.write("#---\n")
        f.write(content)

    # Read and verify there's no metadata (because of the non-# line)
    result, content_offset, metadata_start_offset = fmf_read_frontmatter_raw(file_path)
    assert result is None
    assert content_offset == 0
    assert metadata_start_offset == 0


def test_non_dict_metadata_raises(tmp_path: Path):
    # Frontmatter that parses to a list, not a dict
    file_path = tmp_path / "test_non_dict_metadata.md"
    with open(file_path, "w") as f:
        f.write("---\n")
        f.write("- one\n")
        f.write("- two\n")
        f.write("---\n")
        f.write("Body text\n")

    # Raw read should succeed and return the YAML string
    raw, content_offset, metadata_start = fmf_read_frontmatter_raw(file_path)
    assert raw == "- one\n- two\n"
    assert content_offset > 0
    assert metadata_start == 0

    # Parsed reads should raise FmFormatError because YAML is not a dict
    with pytest.raises(FmFormatError):
        fmf_read_frontmatter(file_path)

    with pytest.raises(FmFormatError):
        fmf_read(file_path)
