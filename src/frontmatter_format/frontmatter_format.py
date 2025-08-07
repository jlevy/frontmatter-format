"""
Python implementation of frontmatter format.
"""

import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from .key_sort import KeySort
from .yaml_util import from_yaml_string, to_yaml_string


class FmFormatError(ValueError):
    """
    Error for frontmatter file format issues.
    """


@dataclass(frozen=True)
class FmDelimiters:
    start: str
    end: str
    prefix: str
    strip_prefixes: list[str]


class FmStyle(Enum):
    """
    The style of frontmatter demarcation to use.

    There are several styles, and synonyms for each style to make it easy to
    remember which to use for each format.
    """

    yaml = md = FmDelimiters("---", "---", "", [])
    html = xml = FmDelimiters("<!---", "--->", "", [])
    hash = python = ruby = csv = FmDelimiters("#---", "#---", "# ", ["# ", "#"])
    slash = rust = cpp = FmDelimiters("//---", "//---", "// ", ["// ", "//"])
    slash_star = c = javascript = css = FmDelimiters("/*---", "---*/", "", [])
    dash = sql = FmDelimiters("----", "----", "-- ", ["-- ", "--"])

    @property
    def start(self) -> str:
        return self.value.start

    @property
    def end(self) -> str:
        return self.value.end

    @property
    def prefix(self) -> str:
        return self.value.prefix

    @property
    def strip_prefixes(self) -> list[str]:
        return self.value.strip_prefixes

    def strip_prefix(self, line: str) -> str:
        for prefix in self.strip_prefixes:
            if line.startswith(prefix):
                return line[len(prefix) :]
        return line


Metadata = dict[str, Any]
"""
Parsed metadata from frontmatter.
"""


def fmf_write(
    path: Path | str,
    content: str,
    metadata: Metadata | str | None,
    style: FmStyle = FmStyle.yaml,
    key_sort: KeySort[str] | None = None,
    make_parents: bool = True,
) -> None:
    """
    Write the given Markdown text content to a file, with associated YAML metadata, in a
    generalized Jekyll-style frontmatter format. Metadata can be a raw string or a dict
    that will be serialized to YAML.
    """
    if isinstance(metadata, str):
        frontmatter_str = metadata
    else:
        frontmatter_str = to_yaml_string(metadata, key_sort=key_sort)

    path = Path(path)
    if make_parents and path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = f"{path}.fmf.write.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            if metadata:
                f.write(style.start)
                f.write("\n")
                for line in frontmatter_str.splitlines():
                    f.write(style.prefix + line)
                    f.write("\n")
                f.write(style.end)
                f.write("\n")

            f.write(content)
        os.replace(tmp_path, path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise e


def _parse_metadata(path: Path | str, metadata_str: str | None) -> Metadata | None:
    if not metadata_str:
        return None
    try:
        parsed = from_yaml_string(metadata_str)
        if not isinstance(parsed, dict):
            raise FmFormatError(
                f"Expected YAML metadata to be a dict, got {type(parsed)}: `{path}`"
            )
        return parsed
    except YAMLError as e:
        raise FmFormatError(f"Error parsing YAML metadata: `{path}`: {e}") from e


def fmf_read(path: Path | str) -> tuple[str, Metadata | None]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format. Auto-detects variant formats for HTML and code
    (Python style) based on whether the prefix is `---` or `<!---` or `#---`.
    Reads the entire file into memory. Parses the metadata as YAML.
    """
    content, metadata_str = fmf_read_raw(path)
    metadata = _parse_metadata(path, metadata_str)
    return content, metadata


def fmf_read_raw(path: Path | str) -> tuple[str, str | None]:
    """
    Reads the full content and raw (unparsed) metadata from the file, both as strings.
    """
    metadata_str, content_offset, _ = fmf_read_frontmatter_raw(path)

    with open(path, encoding="utf-8") as f:
        f.seek(content_offset)
        content = f.read()

    return content, metadata_str


def fmf_read_frontmatter(path: Path | str) -> Metadata | None:
    """
    Reads and parses only the metadata frontmatter from the file.
    Returns None if there is no frontmatter.
    """
    metadata_str, _, _ = fmf_read_frontmatter_raw(path)
    return _parse_metadata(path, metadata_str)


def fmf_read_frontmatter_raw(path: Path | str) -> tuple[str | None, int, int]:
    """
    Reads the metadata frontmatter from the file and returns:

    - the metadata string (or None if no frontmatter found)
    - the content offset (byte position where content begins after frontmatter)
    - the metadata start offset (byte position where metadata begins, which
      will be 0 unless there are initial # lines before the frontmatter)

    Does not parse the metadata or read the body content.
    Returns None, 0, 0 if there is no frontmatter. Safe on binary files.
    """
    metadata_lines: list[str] = []
    in_metadata = False
    metadata_start_offset = 0

    try:
        with open(path, encoding="utf-8") as f:
            # Read the first line to check frontmatter style.
            line = f.readline()
            if not line:
                return None, 0, 0  # Empty file

            first_line = line.rstrip()

            # Special case for hash style with potential initial # lines that
            # are not part of the frontmatter.
            delimiters = None
            if first_line.startswith("#"):
                if first_line == FmStyle.hash.start:
                    # Direct match for #--- on the first line
                    delimiters = FmStyle.hash
                    in_metadata = True
                    metadata_start_offset = 0
                else:
                    # This might be a hash style file with initial # comments.
                    # See through initial # comment lines.
                    f.seek(0)
                    while True:
                        start_pos = f.tell()
                        line = f.readline()
                        if not line:
                            break
                        if line.rstrip() == FmStyle.hash.start:
                            # Found #--- after some initial # lines.
                            delimiters = FmStyle.hash
                            in_metadata = True
                            metadata_start_offset = start_pos
                            break
                        elif not line.startswith("#"):
                            break

            # Standard frontmatter style checks.
            elif first_line == FmStyle.yaml.start:
                delimiters = FmStyle.yaml
                in_metadata = True
                metadata_start_offset = 0
            elif first_line == FmStyle.html.start:
                delimiters = FmStyle.html
                in_metadata = True
                metadata_start_offset = 0
            else:
                # No recognized frontmatter
                return None, 0, 0

            if not in_metadata or not delimiters:
                return None, 0, 0

            # Parse the metadata content between delimiters
            while True:
                line = f.readline()
                if not line:
                    break

                if line.rstrip() == delimiters.end and in_metadata:
                    metadata_str = "".join(
                        delimiters.strip_prefix(mline) for mline in metadata_lines
                    )
                    content_offset = f.tell()
                    return metadata_str, content_offset, metadata_start_offset

                if in_metadata:
                    metadata_lines.append(line)

            if in_metadata:  # End delimiter was never found
                raise FmFormatError(
                    f"Delimiter `{delimiters.end}` for end of frontmatter not found: `{(path)}`"
                )
    except UnicodeDecodeError:
        # Was a binary file.
        pass

    return None, 0, 0


def fmf_has_frontmatter(path: Path | str) -> bool:
    """
    Returns True if the file has frontmatter, False otherwise. Safe on binary files.
    """
    return fmf_read_frontmatter_raw(path)[0] is not None


def fmf_strip_frontmatter(path: Path | str) -> None:
    """
    Strip the metadata frontmatter from the file, in place on the file.
    Does not read the content (except to do a file copy) so should work fairly
    quickly on large files. Does nothing if there is no frontmatter.
    """
    _, content_offset, _ = fmf_read_frontmatter_raw(path)
    if content_offset > 0:
        tmp_path = f"{path}.fmf.strip.tmp"
        try:
            with (
                open(path, encoding="utf-8") as original_file,
                open(tmp_path, "w", encoding="utf-8") as temp_file,
            ):
                original_file.seek(content_offset)
                shutil.copyfileobj(original_file, temp_file)
            os.replace(tmp_path, path)
        except Exception as e:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            raise e


def fmf_insert_frontmatter(
    path: Path | str,
    metadata: Metadata | None,
    fm_style: FmStyle = FmStyle.yaml,
    key_sort: KeySort[str] | None = None,
) -> None:
    """
    Insert metadata as frontmatter into the given file, inserting at the top
    and replacing any existing frontmatter.
    """
    # TODO: Add a flag (default on) to seek past # comments before inserting
    # frontmatter, for compatibility with shebangs and `# /// script` inline
    # dependencies.
    if not metadata:
        return

    if isinstance(metadata, str):
        frontmatter_str = metadata
    else:
        frontmatter_str = to_yaml_string(metadata, key_sort=key_sort)

    # Prepare the new frontmatter.
    frontmatter_lines = [fm_style.start + "\n"]
    if frontmatter_str:
        for line in frontmatter_str.splitlines():
            frontmatter_lines.append(fm_style.prefix + line + "\n")
    frontmatter_lines.append(fm_style.end + "\n")

    tmp_path = f"{path}.fmf.insert.tmp"

    try:
        # Determine where any existing frontmatter ends (content_offset).
        _, content_offset, _ = fmf_read_frontmatter_raw(path)

        with open(tmp_path, "w", encoding="utf-8") as temp_file:
            temp_file.writelines(frontmatter_lines)

            with open(path, encoding="utf-8") as original_file:
                original_file.seek(content_offset)
                shutil.copyfileobj(original_file, temp_file)

        os.replace(tmp_path, path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise e
