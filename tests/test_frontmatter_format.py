import builtins
import os
import stat
import threading
from pathlib import Path
from typing import Any

import pytest

from frontmatter_format import YamlSerializationError, fmf_split_frontmatter
from frontmatter_format.frontmatter_format import (
    FmFormatError,
    FmStyle,
    fmf_has_frontmatter,
    fmf_insert_frontmatter,
    fmf_read,
    fmf_read_frontmatter,
    fmf_read_frontmatter_raw,
    fmf_read_raw,
    fmf_strip_frontmatter,
    fmf_write,
)
from frontmatter_format.key_sort import custom_key_sort
from frontmatter_format.yaml_util import dump_yaml, from_yaml_string, to_yaml_string


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


def test_fmf_write_expands_shared_mapping_metadata(tmp_path: Path):
    file_path = tmp_path / "shared-metadata.md"
    shared_value = {"base_case": 2.0}
    metadata = {"model_a": shared_value, "model_b": shared_value}

    fmf_write(file_path, "Body\n", metadata)

    assert file_path.read_text(encoding="utf-8") == (
        "---\nmodel_a:\n  base_case: 2.0\nmodel_b:\n  base_case: 2.0\n---\nBody\n"
    )


def test_fmf_write_preserves_raw_yaml_aliases(tmp_path: Path):
    file_path = tmp_path / "raw-alias.md"
    raw_metadata = "model_a: &model\n  base_case: 2.0\nmodel_b: *model"

    fmf_write(file_path, "Body\n", raw_metadata)

    assert file_path.read_text(encoding="utf-8") == (
        "---\nmodel_a: &model\n  base_case: 2.0\nmodel_b: *model\n---\nBody\n"
    )


def test_fmf_write_rejects_cycles_without_leaving_files(tmp_path: Path):
    file_path = tmp_path / "cyclic-metadata.md"
    cyclic_value: dict[str, object] = {}
    cyclic_value["self"] = cyclic_value

    with pytest.raises(YamlSerializationError, match=r"cyclic object graph"):
        fmf_write(file_path, "Body\n", {"cyclic": cyclic_value})

    assert not file_path.exists()
    assert list(tmp_path.iterdir()) == []


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


def test_fmf_split_frontmatter_basic():
    content = "---\ntitle: Hello\ntags: [a, b]\n---\n\n# Body\n\nText.\n"
    metadata_str, content_offset, metadata_start = fmf_split_frontmatter(content)
    assert metadata_str == "title: Hello\ntags: [a, b]\n"
    assert metadata_start == 0
    # Offsets are character positions: the slices are exact.
    assert content[:content_offset] == "---\ntitle: Hello\ntags: [a, b]\n---\n"
    assert content[content_offset:] == "\n# Body\n\nText.\n"


def test_fmf_split_frontmatter_matches_file_reader(tmp_path: Path):
    content = "---\ntitle: T\nauthor: A\n---\nBody only.\n"
    (tmp_path / "doc.md").write_text(content, encoding="utf-8")
    file_meta, _, file_start = fmf_read_frontmatter_raw(tmp_path / "doc.md")
    str_meta, _, str_start = fmf_split_frontmatter(content)
    # Same metadata string and start; for ASCII content the offsets also agree.
    assert str_meta == file_meta
    assert str_start == file_start


def test_fmf_split_frontmatter_offsets_are_code_points():
    # A multi-byte char in the frontmatter: character offsets must slice correctly where
    # byte offsets would not.
    content = "---\ntitle: café — déjà\n---\nbody\n"
    _, content_offset, _ = fmf_split_frontmatter(content)
    assert content[content_offset:] == "body\n"


def test_fmf_split_frontmatter_no_frontmatter():
    assert fmf_split_frontmatter("# Just a heading\n\nText.\n") == (None, 0, 0)
    # Five dashes is not a frontmatter delimiter.
    assert fmf_split_frontmatter("-----\nnot frontmatter\n") == (None, 0, 0)


def test_fmf_split_frontmatter_unclosed_delimiter():
    # A bare leading `---` with no closing delimiter: strict raises, lenient returns None
    # (so a caller can treat it as a Markdown thematic break, not frontmatter).
    unclosed = "---\n\nA thematic break rule above, no closing delimiter.\n"
    with pytest.raises(FmFormatError):
        fmf_split_frontmatter(unclosed)
    assert fmf_split_frontmatter(unclosed, strict=False) == (None, 0, 0)


@pytest.mark.parametrize("style", list(FmStyle))
def test_fmf_split_frontmatter_supports_every_style(style: FmStyle):
    metadata_line = f"{style.prefix}title: All styles\n"
    frontmatter = f"{style.start}\n{metadata_line}{style.end}\n"
    content = f"{frontmatter}body\n"

    metadata_str, content_offset, metadata_start = fmf_split_frontmatter(content)

    assert metadata_str == "title: All styles\n"
    assert metadata_start == 0
    assert content[:content_offset] == frontmatter
    assert content[content_offset:] == "body\n"


@pytest.mark.parametrize(
    "newline",
    ["\n", "\r\n", "\r"],
    ids=["LF", "CRLF", "CR"],
)
def test_fmf_split_frontmatter_preserves_metadata_newlines(newline: str):
    metadata = f"title: Original newlines{newline}"
    frontmatter = f"---{newline}{metadata}---{newline}"
    content = f"{frontmatter}body{newline}"

    metadata_str, content_offset, metadata_start = fmf_split_frontmatter(content)

    assert metadata_str == metadata
    assert metadata_start == 0
    assert content[:content_offset] == frontmatter
    assert content[content_offset:] == f"body{newline}"


def test_fmf_split_frontmatter_preserves_crlf_that_file_reader_normalizes(tmp_path: Path):
    content = "---\r\ntitle: Original newlines\r\n---\r\nbody\r\n"
    file_path = tmp_path / "crlf.md"
    file_path.write_bytes(content.encode("utf-8"))

    string_metadata, string_offset, _ = fmf_split_frontmatter(content)
    file_metadata, file_offset, _ = fmf_read_frontmatter_raw(file_path)

    assert string_metadata == "title: Original newlines\r\n"
    assert content[string_offset:] == "body\r\n"
    assert file_metadata == "title: Original newlines\n"
    with open(file_path, encoding="utf-8") as stream:
        stream.seek(file_offset)
        assert stream.read() == "body\n"


def test_fmf_split_frontmatter_hash_preamble_offsets():
    preamble = "#!/usr/bin/env python\r\n# Script metadata follows\r\n"
    frontmatter = "#---\r\n# title: Hash preamble\r\n#---\r\n"
    content = f"{preamble}{frontmatter}print('body')\r\n"

    metadata_str, content_offset, metadata_start = fmf_split_frontmatter(content)

    assert metadata_str == "title: Hash preamble\r\n"
    assert metadata_start == len(preamble)
    assert content[:metadata_start] == preamble
    assert content[metadata_start:content_offset] == frontmatter
    assert content[content_offset:] == "print('body')\r\n"


def test_fmf_split_frontmatter_closing_delimiter_without_newline():
    content = "---\ntitle: No body\n---"

    metadata_str, content_offset, metadata_start = fmf_split_frontmatter(content)

    assert metadata_str == "title: No body\n"
    assert content_offset == len(content)
    assert metadata_start == 0
    assert content[:content_offset] == content
    assert content[content_offset:] == ""


@pytest.mark.parametrize(
    "separator", ["\u2028", "\u2029", "\u0085", "\v", "\f", "\x1c", "\x1d", "\x1e"]
)
def test_fmf_split_frontmatter_rejects_non_format_line_separators(separator: str):
    content = f"---{separator}title: Not frontmatter{separator}---{separator}body"

    assert fmf_split_frontmatter(content) == (None, 0, 0)


# Writers split metadata only at the line endings the readers recognize (fmf-uj5a).

# Characters `str.splitlines()` breaks at but the readers do not: the file reader's universal
# newlines and the string reader split only at LF, CRLF and CR.
NON_LINE_ENDING_SEPARATORS = [" ", " ", "\u0085", "\v", "\f", "\x1c", "\x1d", "\x1e"]
SEPARATOR_IDS = ["LS", "PS", "NEL", "VT", "FF", "FS", "GS", "RS"]


@pytest.mark.parametrize("separator", NON_LINE_ENDING_SEPARATORS, ids=SEPARATOR_IDS)
@pytest.mark.parametrize("style", list(FmStyle))
def test_fmf_write_raw_metadata_round_trips_separators(
    tmp_path: Path, style: FmStyle, separator: str
):
    file_path = tmp_path / "doc.txt"
    raw_metadata = f'a: "x{separator}y"\nb: 1\n'

    fmf_write(file_path, "body\n", raw_metadata, style=style)

    assert fmf_read_raw(file_path) == ("body\n", raw_metadata)


@pytest.mark.parametrize("separator", NON_LINE_ENDING_SEPARATORS, ids=SEPARATOR_IDS)
@pytest.mark.parametrize("style", list(FmStyle))
def test_writers_round_trip_dict_metadata_with_separators(
    tmp_path: Path, style: FmStyle, separator: str
):
    metadata = {"a": f"x{separator}y", "b": 1}
    # The frontmatter layer must read back what the YAML layer alone reads back.
    yaml_reading = from_yaml_string(to_yaml_string(metadata))
    if separator != "\u0085":
        assert yaml_reading == metadata
    # ruamel writes a NEL raw inside a quoted scalar and folds it to a space on reading,
    # with or without frontmatter, so only the YAML layer's own reading is expected.

    written = tmp_path / "written.txt"
    fmf_write(written, "body\n", metadata, style=style)
    assert fmf_read(written) == ("body\n", yaml_reading)

    inserted = tmp_path / "inserted.txt"
    inserted.write_text("body\n", encoding="utf-8")
    fmf_insert_frontmatter(inserted, metadata, fm_style=style)
    assert fmf_read(inserted) == ("body\n", yaml_reading)


def test_fmf_write_raw_metadata_splits_at_lf_crlf_and_cr(tmp_path: Path):
    file_path = tmp_path / "doc.py"

    fmf_write(file_path, "body\n", "a: 1\r\nb: 2\rc: 3\nd: 4", style=FmStyle.hash)

    assert file_path.read_bytes() == b"#---\n# a: 1\n# b: 2\n# c: 3\n# d: 4\n#---\nbody\n"


# Insert and strip keep the `#` lines before hash-style frontmatter (fmf-21r5).

HASH_PREAMBLE = (
    "#!/usr/bin/env python\n"
    "# /// script\n"
    '# requires-python = ">=3.12"\n'
    "# dependencies = []\n"
    "# ///\n"
    "# Copyright: café ☕\n"
)


def test_fmf_insert_frontmatter_keeps_hash_preamble(tmp_path: Path):
    file_path = tmp_path / "script.py"
    file_path.write_text(f"{HASH_PREAMBLE}#---\n# a: 1\n#---\nprint()\n", encoding="utf-8")

    fmf_insert_frontmatter(file_path, {"b": 2}, fm_style=FmStyle.hash)

    assert file_path.read_text(encoding="utf-8") == f"{HASH_PREAMBLE}#---\n# b: 2\n#---\nprint()\n"
    assert fmf_read(file_path) == ("print()\n", {"b": 2})
    _, _, metadata_start_offset = fmf_read_frontmatter_raw(file_path)
    assert metadata_start_offset == len(HASH_PREAMBLE.encode("utf-8"))


def test_fmf_strip_frontmatter_keeps_hash_preamble(tmp_path: Path):
    file_path = tmp_path / "script.py"
    file_path.write_text(f"{HASH_PREAMBLE}#---\n# a: 1\n#---\nprint()\n", encoding="utf-8")

    fmf_strip_frontmatter(file_path)

    assert file_path.read_text(encoding="utf-8") == f"{HASH_PREAMBLE}print()\n"


def test_insert_and_strip_keep_long_crlf_hash_preamble(tmp_path: Path):
    # A preamble longer than the text reader's chunk size, with CRLF line endings, which
    # the writers normalize the same way as the body.
    preamble_lines = [f"# preamble line {i}: {'ü' * 40}" for i in range(400)]
    preamble = "".join(f"{line}\r\n" for line in preamble_lines)
    file_path = tmp_path / "script.py"
    file_path.write_bytes(f"{preamble}#---\r\n# a: 1\r\n#---\r\nbody\r\n".encode())
    expected_preamble = "".join(f"{line}\n" for line in preamble_lines)

    fmf_insert_frontmatter(file_path, {"b": 2}, fm_style=FmStyle.hash)
    assert file_path.read_text(encoding="utf-8") == f"{expected_preamble}#---\n# b: 2\n#---\nbody\n"

    fmf_strip_frontmatter(file_path)
    assert file_path.read_text(encoding="utf-8") == f"{expected_preamble}body\n"


@pytest.mark.parametrize("style", [s for s in FmStyle if s is not FmStyle.hash])
def test_fmf_insert_frontmatter_rejects_non_hash_style_after_hash_preamble(
    tmp_path: Path, style: FmStyle
):
    # Only hash-style frontmatter may follow `#` lines, so another style there would not
    # read back, and dropping the lines would lose them.
    file_path = tmp_path / "script.py"
    original = f"{HASH_PREAMBLE}#---\n# a: 1\n#---\nprint()\n"
    file_path.write_text(original, encoding="utf-8")

    with pytest.raises(FmFormatError, match="hash-style"):
        fmf_insert_frontmatter(file_path, {"b": 2}, fm_style=style)

    assert file_path.read_text(encoding="utf-8") == original
    assert list(tmp_path.iterdir()) == [file_path]


# Writers keep the target's file mode (fmf-mkor).

needs_posix_modes = pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")


def _run_writer(writer: str, file_path: Path) -> None:
    if writer == "fmf_write":
        fmf_write(file_path, "print()\n", {"b": 2}, style=FmStyle.hash)
    elif writer == "fmf_insert_frontmatter":
        fmf_insert_frontmatter(file_path, {"b": 2}, fm_style=FmStyle.hash)
    else:
        fmf_strip_frontmatter(file_path)


WRITERS = ["fmf_write", "fmf_insert_frontmatter", "fmf_strip_frontmatter"]


@needs_posix_modes
@pytest.mark.parametrize("mode", [0o755, 0o700, 0o600, 0o640, 0o444])
@pytest.mark.parametrize("writer", WRITERS)
def test_writers_keep_existing_file_mode(tmp_path: Path, writer: str, mode: int):
    file_path = tmp_path / "script.py"
    file_path.write_text("#---\n# a: 1\n#---\nprint()\n", encoding="utf-8")
    file_path.chmod(mode)

    _run_writer(writer, file_path)

    assert stat.S_IMODE(file_path.stat().st_mode) == mode
    assert list(tmp_path.iterdir()) == [file_path]


@pytest.mark.parametrize("writer", WRITERS)
def test_writers_still_write_where_chmod_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer: str
):
    # Some filesystems (some FUSE mounts, Android shared storage) refuse chmod. Keeping the
    # mode is best effort there: the write still happens, as it did before modes were kept.
    file_path = tmp_path / "script.py"
    file_path.write_text("#---\n# a: 1\n#---\nprint()\n", encoding="utf-8")

    def refuse_chmod(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "chmod", refuse_chmod)
    _run_writer(writer, file_path)
    monkeypatch.undo()

    expected = "print()\n" if writer == "fmf_strip_frontmatter" else "#---\n# b: 2\n#---\nprint()\n"
    assert file_path.read_text(encoding="utf-8") == expected
    assert list(tmp_path.iterdir()) == [file_path]


@needs_posix_modes
def test_fmf_write_gives_new_file_the_umask_default_mode(tmp_path: Path):
    file_path = tmp_path / "new.md"
    old_umask = os.umask(0o027)
    try:
        fmf_write(file_path, "body\n", {"a": 1})
    finally:
        os.umask(old_umask)

    assert stat.S_IMODE(file_path.stat().st_mode) == 0o640


# Writers use unique temp files beside the target (fmf-roi5).


def test_writers_use_unique_temp_files_beside_the_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    file_path = tmp_path / "doc.md"
    file_path.write_text("---\na: 1\n---\nbody\n", encoding="utf-8")
    replaced: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def spy_replace(src: Any, dst: Any) -> None:
        replaced.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy_replace)
    for _ in range(2):
        fmf_write(file_path, "body\n", {"a": 2})
        fmf_insert_frontmatter(file_path, {"a": 3})
        fmf_strip_frontmatter(file_path)

    temp_paths = [src for src, _ in replaced]
    assert len(replaced) == 6
    assert len(set(temp_paths)) == len(temp_paths)
    assert all(src.parent == tmp_path for src in temp_paths)
    assert all(dst == file_path for _, dst in replaced)
    assert list(tmp_path.iterdir()) == [file_path]


def test_writers_leave_other_writers_temp_files_alone(tmp_path: Path):
    file_path = tmp_path / "doc.md"
    file_path.write_text("---\na: 1\n---\nbody\n", encoding="utf-8")
    # Files at the fixed temp names earlier releases used, standing for another writer's
    # temp file that is still being written.
    others = {
        tmp_path / f"doc.md.fmf.{name}.tmp": f"another {name} in progress\n"
        for name in ("write", "insert", "strip")
    }
    for other_path, text in others.items():
        other_path.write_text(text, encoding="utf-8")

    fmf_write(file_path, "body\n", {"a": 2})
    fmf_insert_frontmatter(file_path, {"a": 3})
    fmf_strip_frontmatter(file_path)

    assert file_path.read_text(encoding="utf-8") == "body\n"
    for other_path, text in others.items():
        assert other_path.read_text(encoding="utf-8") == text
    assert sorted(tmp_path.iterdir()) == sorted([file_path, *others])


def test_concurrent_fmf_write_to_one_target(tmp_path: Path):
    file_path = tmp_path / "doc.md"
    errors: list[BaseException] = []

    def write_repeatedly(writer: int) -> None:
        try:
            for _ in range(25):
                fmf_write(file_path, f"body {writer}\n", {"writer": writer})
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=write_repeatedly, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    content, metadata = fmf_read(file_path)
    assert metadata is not None
    assert content == f"body {metadata['writer']}\n"
    assert list(tmp_path.iterdir()) == [file_path]


def test_fmf_insert_frontmatter_failure_leaves_file_and_no_temp(tmp_path: Path):
    file_path = tmp_path / "binary.dat"
    original = b"\xff\xfe not UTF-8 \x80\n"
    file_path.write_bytes(original)

    with pytest.raises(UnicodeDecodeError):
        fmf_insert_frontmatter(file_path, {"a": 1})

    assert file_path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [file_path]


# Blank, comment-only and null frontmatter read as no metadata, like empty frontmatter
# (fmf-9qzn).


@pytest.mark.parametrize(
    "file_text",
    [
        "---\n---\nbody\n",
        "---\n\n---\nbody\n",
        "---\n  \n\n---\nbody\n",
        "---\n# only a comment\n---\nbody\n",
        "---\n~\n---\nbody\n",
        "---\nnull\n---\nbody\n",
        "#---\n# # only a comment\n#---\nbody\n",
        "#---\n# ~\n#---\nbody\n",
    ],
    ids=["empty", "blank", "whitespace", "comment", "tilde", "null", "hash-comment", "hash-tilde"],
)
def test_blank_comment_or_null_frontmatter_reads_as_none(tmp_path: Path, file_text: str):
    file_path = tmp_path / "doc.md"
    file_path.write_text(file_text, encoding="utf-8")

    assert fmf_read(file_path) == ("body\n", None)
    assert fmf_read_frontmatter(file_path) is None
    assert fmf_has_frontmatter(file_path) is True


@pytest.mark.parametrize("metadata_text", ["- one\n", "just text\n", "42\n", "false\n", "''\n"])
def test_non_dict_non_null_metadata_still_raises(tmp_path: Path, metadata_text: str):
    file_path = tmp_path / "doc.md"
    file_path.write_text(f"---\n{metadata_text}---\nbody\n", encoding="utf-8")

    with pytest.raises(FmFormatError, match="Expected YAML metadata to be a dict"):
        fmf_read(file_path)
    with pytest.raises(FmFormatError, match="Expected YAML metadata to be a dict"):
        fmf_read_frontmatter(file_path)


# fmf_has_frontmatter reports False, not an error, for an unclosed delimiter (fmf-0qru).


@pytest.mark.parametrize("style", list(FmStyle))
def test_fmf_has_frontmatter_detects_every_style(tmp_path: Path, style: FmStyle):
    closed = tmp_path / "closed.txt"
    closed.write_text(f"{style.start}\n{style.prefix}a: 1\n{style.end}\nbody\n", encoding="utf-8")
    unclosed = tmp_path / "unclosed.txt"
    unclosed.write_text(f"{style.start}\n{style.prefix}a: 1\nbody\n", encoding="utf-8")

    assert fmf_has_frontmatter(closed) is True
    assert fmf_has_frontmatter(unclosed) is False
    # The strict readers still raise on the unclosed delimiter.
    with pytest.raises(FmFormatError, match="end of frontmatter not found"):
        fmf_read(unclosed)


def test_fmf_has_frontmatter_false_for_markdown_thematic_break(tmp_path: Path):
    file_path = tmp_path / "doc.md"
    file_path.write_text("---\n\nA thematic break above, no closing delimiter.\n")

    assert fmf_has_frontmatter(file_path) is False


def test_fmf_has_frontmatter_other_cases(tmp_path: Path):
    preamble = tmp_path / "preamble.py"
    preamble.write_text(f"{HASH_PREAMBLE}#---\n# a: 1\n#---\nprint()\n", encoding="utf-8")
    unclosed_preamble = tmp_path / "unclosed_preamble.py"
    unclosed_preamble.write_text(f"{HASH_PREAMBLE}#---\n# a: 1\nprint()\n", encoding="utf-8")
    plain = tmp_path / "plain.md"
    plain.write_text("# Heading\n\nText.\n", encoding="utf-8")
    empty = tmp_path / "empty.md"
    empty.touch()
    binary = tmp_path / "binary.dat"
    binary.write_bytes(b"---\n\xff\xfe\x80\n---\n")

    assert fmf_has_frontmatter(preamble) is True
    assert fmf_has_frontmatter(unclosed_preamble) is False
    assert fmf_has_frontmatter(plain) is False
    assert fmf_has_frontmatter(empty) is False
    assert fmf_has_frontmatter(binary) is False


# fmf_read_raw opens the file once (fmf-hker), with the same results.


def test_fmf_read_raw_opens_the_file_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    file_path = tmp_path / "doc.md"
    file_path.write_text("---\na: 1\n---\nbody\n", encoding="utf-8")
    opened: list[Path] = []
    real_open = builtins.open

    def spy_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, Path)):
            opened.append(Path(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    result = fmf_read_raw(file_path)
    monkeypatch.undo()

    assert result == ("body\n", "a: 1\n")
    assert opened == [file_path]


@pytest.mark.parametrize(
    ("file_text", "expected"),
    [
        ("---\na: 1\n---\nbody\n", ("body\n", "a: 1\n")),
        ("---\r\na: 1\r\n---\r\nbody\r\n", ("body\n", "a: 1\n")),
        ("---\na: 1\n---", ("", "a: 1\n")),
        ("no frontmatter\n", ("no frontmatter\n", None)),
        ("", ("", None)),
        ("-----\nhello\n", ("-----\nhello\n", None)),
        (f"{HASH_PREAMBLE}#---\n# a: 1\n#---\nprint()\n", ("print()\n", "a: 1\n")),
        ("---\nt: café\n---\n" + "é" * 10000 + "\n", ("é" * 10000 + "\n", "t: café\n")),
    ],
    ids=["lf", "crlf", "no-body", "none", "empty", "five-dashes", "preamble", "long-body"],
)
def test_fmf_read_raw_results(tmp_path: Path, file_text: str, expected: tuple[str, str | None]):
    file_path = tmp_path / "doc.txt"
    file_path.write_bytes(file_text.encode("utf-8"))

    assert fmf_read_raw(file_path) == expected


@pytest.mark.parametrize(
    "file_bytes",
    [b"\xff\xfe\x80 binary\n", b"---\na: 1\n---\n" + b"x" * 20000 + b"\xff\n"],
    ids=["binary", "bad-body"],
)
def test_fmf_read_raw_raises_on_non_utf8(tmp_path: Path, file_bytes: bytes):
    file_path = tmp_path / "doc.dat"
    file_path.write_bytes(file_bytes)

    with pytest.raises(UnicodeDecodeError):
        fmf_read_raw(file_path)


def test_fmf_read_raw_raises_on_unclosed_delimiter(tmp_path: Path):
    file_path = tmp_path / "doc.md"
    file_path.write_text("---\na: 1\nbody\n", encoding="utf-8")

    with pytest.raises(FmFormatError, match="end of frontmatter not found"):
        fmf_read_raw(file_path)
