"""
Python implementation of frontmatter format.
"""

import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast, Dict, List, Optional, Tuple

from ruamel.yaml.error import YAMLError

from .yaml_util import from_yaml_string, KeySort, to_yaml_string


class FmFormatError(ValueError):
    """
    Error for frontmatter file format issues.
    """


@dataclass(frozen=True)
class FmDelimiters:
    start: str
    end: str
    prefix: str
    strip_prefixes: List[str]


class FmStyle(Enum):
    """
    The style of frontmatter demarcation to use.
    """

    yaml = FmDelimiters("---", "---", "", [])
    html = FmDelimiters("<!---", "--->", "", [])
    hash = FmDelimiters("#---", "#---", "# ", ["# ", "#"])
    slash = FmDelimiters("//---", "//---", "// ", ["// ", "//"])
    slash_star = FmDelimiters("/*---", "---*/", "", [])
    dash = FmDelimiters("----", "----", "-- ", ["-- ", "--"])

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
    def strip_prefixes(self) -> List[str]:
        return self.value.strip_prefixes

    def strip_prefix(self, line: str) -> str:
        for prefix in self.strip_prefixes:
            if line.startswith(prefix):
                return line[len(prefix) :]
        return line


Metadata = Dict[str, Any]
"""
Parsed metadata from frontmatter.
"""


def fmf_write(
    path: Path | str,
    content: str,
    metadata: Optional[Metadata | str],
    style: FmStyle = FmStyle.yaml,
    key_sort: Optional[KeySort] = None,
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


def fmf_read(path: Path | str) -> Tuple[str, Optional[Metadata]]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format. Auto-detects variant formats for HTML and code
    (Python style) based on whether the prefix is `---` or `<!---` or `#---`.
    Reads the entire file into memory. Parses the metadata as YAML.
    """
    content, metadata_str = fmf_read_raw(path)
    metadata = None
    if metadata_str:
        try:
            metadata = from_yaml_string(metadata_str)
        except YAMLError as e:
            raise FmFormatError(f"Error parsing YAML metadata: `{path}`: {e}") from e
        if not isinstance(metadata, dict):
            raise FmFormatError(f"Invalid metadata type: {type(metadata)}")
        metadata = cast(Metadata, metadata)
    return content, metadata


def fmf_read_raw(path: Path | str) -> Tuple[str, Optional[str]]:
    """
    Reads the full content and raw (unparsed) metadata from the file, both as strings.
    """
    metadata_str, offset = fmf_read_frontmatter_raw(path)

    with open(path, "r", encoding="utf-8") as f:
        f.seek(offset)
        content = f.read()

    return content, metadata_str


def fmf_read_frontmatter_raw(path: Path | str) -> Tuple[Optional[str], int]:
    """
    Reads the metadata frontmatter from the file and returns the metadata string and
    the seek offset of the beginning of the content. Does not parse the metadata.
    Does not read the body content into memory.
    """
    metadata_lines: List[str] = []
    in_metadata = False

    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline().rstrip()

        if first_line == FmStyle.yaml.start:
            delimiters = FmStyle.yaml
            in_metadata = True
        elif first_line == FmStyle.html.start:
            delimiters = FmStyle.html
            in_metadata = True
        elif first_line == FmStyle.hash.start:
            delimiters = FmStyle.hash
            in_metadata = True
        else:
            # Empty file or no recognized frontmatter.
            return None, 0

        while True:
            line = f.readline()
            if not line:
                break

            if line.rstrip() == delimiters.end and in_metadata:
                metadata_str = "".join(delimiters.strip_prefix(mline) for mline in metadata_lines)
                return metadata_str, f.tell()

            if in_metadata:
                metadata_lines.append(line)

        if in_metadata:  # If still true, the end delimiter was never found
            raise FmFormatError(
                f"Delimiter `{delimiters.end}` for end of frontmatter not found: `{(path)}`"
            )

    return None, 0


def fmf_strip_frontmatter(path: Path | str) -> None:
    """
    Strip the metadata frontmatter from the file, in place on the file.
    Does not read the content (except to do a file copy) so should work fairly
    quickly on large files. Does nothing if there is no frontmatter.
    """
    _, offset = fmf_read_frontmatter_raw(path)
    if offset > 0:
        tmp_path = f"{path}.fmf.strip.tmp"
        try:
            with open(path, "r", encoding="utf-8") as original_file, open(
                tmp_path, "w", encoding="utf-8"
            ) as temp_file:
                original_file.seek(offset)
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
    metadata: Optional[Metadata],
    fm_style: FmStyle = FmStyle.yaml,
    key_sort: Optional[KeySort] = None,
) -> None:
    """
    Insert metadata as frontmatter into the given file, inserting at the top
    and replacing any existing frontmatter.
    """
    if metadata is None:
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
        # Determine where any existing frontmatter ends (offset).
        _, offset = fmf_read_frontmatter_raw(path)

        with open(tmp_path, "w", encoding="utf-8") as temp_file:
            temp_file.writelines(frontmatter_lines)

            with open(path, "r", encoding="utf-8") as original_file:
                original_file.seek(offset)
                shutil.copyfileobj(original_file, temp_file)

        os.replace(tmp_path, path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise e
