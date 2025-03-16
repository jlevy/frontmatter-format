import os
from pathlib import Path

from frontmatter_format.frontmatter_format import (
    FmStyle,
    fmf_insert_frontmatter,
    fmf_read,
    fmf_read_frontmatter_raw,
    fmf_strip_frontmatter,
    fmf_write,
)
from frontmatter_format.key_sort import custom_key_sort
from frontmatter_format.yaml_util import dump_yaml


def test_fmf_basic():
    os.makedirs("tmp", exist_ok=True)

    # Test with Markdown.
    file_path_md = "tmp/test_write.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_md, content_md, metadata_md)
    with open(file_path_md) as f:
        lines = f.readlines()
    assert lines[0] == FmStyle.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading Markdown.
    file_path_md = "tmp/test_read.md"
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
    file_path_html = "tmp/test_write.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_html, content_html, metadata_html, style=FmStyle.html)
    with open(file_path_html) as f:
        lines = f.readlines()
    assert lines[0] == FmStyle.html.start + "\n"
    assert lines[-1].strip() == content_html
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading HTML.
    file_path_html = "tmp/test_read.html"
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
    file_path_code = "tmp/test_write_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_code, content_code, metadata_code, style=FmStyle.hash)
    with open(file_path_code) as f:
        lines = f.readlines()
    assert lines[0] == FmStyle.hash.start + "\n"
    assert lines[-1].strip() == content_code
    assert "# title: Test Title\n" in lines
    assert "# author: Test Author\n" in lines

    # Test reading code frontmatter.
    file_path_code = "tmp/test_read_code.py"
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


def test_fmf_with_custom_key_sort():
    os.makedirs("tmp", exist_ok=True)

    # Test with Markdown.
    file_path_md = "tmp/test_write_custom_sort.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author", "date": "2022-01-01"}
    fmf_write(file_path_md, content_md, metadata_md, key_sort=custom_key_sort(["date", "title"]))
    with open(file_path_md) as f:
        lines = f.readlines()
    assert lines[0] == FmStyle.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    # Check that the priority keys come first in the order they are in the list
    assert lines[1].strip() == "date: '2022-01-01'"
    assert lines[2].strip() == "title: Test Title"
    assert lines[3].strip() == "author: Test Author"


def test_fmf_metadata():
    os.makedirs("tmp", exist_ok=True)

    # Test offset.
    file_path = "tmp/test_offset.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path, content, metadata)
    result, offset = fmf_read_frontmatter_raw(file_path)
    assert result == """title: Test Title\nauthor: Test Author\n"""
    assert offset == len(result) + 2 * (len("---") + 1)

    # Test a zero-length file.
    zero_length_file = "tmp/empty_file.txt"
    Path(zero_length_file).touch()

    result, offset = fmf_read_frontmatter_raw(zero_length_file)
    assert (result, offset) == (None, 0)

    # Test stripping metadata from Markdown.
    file_path = "tmp/test_strip_metadata.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path, content, metadata)
    fmf_strip_frontmatter(file_path)
    with open(file_path) as f:
        stripped_content = f.read()
    assert stripped_content.strip() == content

    # Test inserting metadata into a file without frontmatter.
    file_path = "tmp/test_insert_no_frontmatter.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    with open(file_path, "w") as f:
        f.write(content)
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
