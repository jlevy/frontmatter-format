"""
Python implementation of frontmatter format.
"""

import shutil
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Any, TextIO

from ruamel.yaml.error import YAMLError

from ._atomic_write import atomic_write_text
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


def _split_lines(text: str) -> list[str]:
    """
    Split text into lines at LF, CRLF and CR, the line endings the readers recognize,
    dropping the line endings and the empty string after a final one. Unlike
    `str.splitlines()`, does not split at the other characters Unicode treats as line
    boundaries (LS, PS, NEL, VT, FF, FS, GS and RS), which a YAML value can hold, so
    writing a value that holds one never breaks its line.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


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

    Writes atomically, through a uniquely named temp file in the same directory. A file
    that is replaced keeps its mode; a new file gets the default mode (0o666 less the
    umask).
    """
    if isinstance(metadata, str):
        frontmatter_str = metadata
    else:
        frontmatter_str = to_yaml_string(metadata, key_sort=key_sort)

    path = Path(path)
    if make_parents and path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    with atomic_write_text(path, "write") as f:
        if metadata:
            f.write(style.start)
            f.write("\n")
            for line in _split_lines(frontmatter_str):
                f.write(style.prefix + line)
                f.write("\n")
            f.write(style.end)
            f.write("\n")

        f.write(content)


def _parse_metadata(path: Path | str, metadata_str: str | None) -> Metadata | None:
    if not metadata_str:
        return None
    try:
        parsed = from_yaml_string(metadata_str)
    except YAMLError as e:
        raise FmFormatError(f"Error parsing YAML metadata: `{path}`: {e}") from e
    if parsed is None:
        # Blank, comment-only or null (`~`) frontmatter holds no value: no metadata, as
        # for empty frontmatter.
        return None
    if not isinstance(parsed, dict):
        raise FmFormatError(f"Expected YAML metadata to be a dict, got {type(parsed)}: `{path}`")
    return parsed


def fmf_read(path: Path | str) -> tuple[str, Metadata | None]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format. Auto-detects variant formats for HTML and code
    (Python style) based on whether the prefix is `---` or `<!---` or `#---`.
    Reads the entire file into memory. Parses the metadata as YAML.

    The metadata is None when there is no frontmatter, or when the frontmatter holds no
    YAML value: empty, blank, only comments, or a YAML null such as `~`. Raises
    `FmFormatError` when the frontmatter holds any other value that is not a mapping.
    """
    content, metadata_str = fmf_read_raw(path)
    metadata = _parse_metadata(path, metadata_str)
    return content, metadata


def fmf_read_raw(path: Path | str) -> tuple[str, str | None]:
    """
    Reads the full content and raw (unparsed) metadata from the file, both as strings.
    """
    with open(path, encoding="utf-8") as stream:
        metadata_str, content_offset, _ = _read_frontmatter_file_stream(stream, path)
        # A file that is not UTF-8 reads as having no frontmatter, at offset 0, so this
        # read raises its decode error.
        stream.seek(content_offset)
        content = stream.read()

    return content, metadata_str


def fmf_read_frontmatter(path: Path | str) -> Metadata | None:
    """
    Reads and parses only the metadata frontmatter from the file.

    Returns None if there is no frontmatter, or if the frontmatter holds no YAML value:
    empty, blank, only comments, or a YAML null such as `~`. Raises `FmFormatError` when
    the frontmatter holds any other value that is not a mapping.
    """
    metadata_str, _, _ = fmf_read_frontmatter_raw(path)
    return _parse_metadata(path, metadata_str)


def _read_frontmatter_stream(
    stream: TextIO,
    *,
    strict: bool,
    source: Path | str | None = None,
) -> tuple[str | None, int, int]:
    """Read frontmatter from a seekable text stream using the stream's offsets."""
    metadata_lines: list[str] = []
    metadata_start_offset = 0

    line = stream.readline()
    if not line:
        return None, 0, 0

    first_line = line.rstrip()
    delimiters: FmStyle | None = None

    if first_line.startswith("#"):
        if first_line == FmStyle.hash.start:
            delimiters = FmStyle.hash
        else:
            stream.seek(0)
            while True:
                start_pos = stream.tell()
                line = stream.readline()
                if not line:
                    break
                if line.rstrip() == FmStyle.hash.start:
                    delimiters = FmStyle.hash
                    metadata_start_offset = start_pos
                    break
                if not line.startswith("#"):
                    break
    else:
        for style in (
            FmStyle.yaml,
            FmStyle.html,
            FmStyle.slash,
            FmStyle.slash_star,
            FmStyle.dash,
        ):
            if first_line == style.start:
                delimiters = style
                break

    if delimiters is None:
        return None, 0, 0

    while True:
        line = stream.readline()
        if not line:
            break

        if line.rstrip() == delimiters.end:
            metadata_str = "".join(
                delimiters.strip_prefix(metadata_line) for metadata_line in metadata_lines
            )
            return metadata_str, stream.tell(), metadata_start_offset

        metadata_lines.append(line)

    if strict:
        source_suffix = f": `{source}`" if source is not None else ""
        raise FmFormatError(
            f"Delimiter `{delimiters.end}` for end of frontmatter not found{source_suffix}"
        )

    return None, 0, 0


def _read_frontmatter_file_stream(
    stream: TextIO, path: Path | str, *, strict: bool = True
) -> tuple[str | None, int, int]:
    """
    `_read_frontmatter_stream` on a file opened as UTF-8 text: a file that is not UTF-8
    has no frontmatter.
    """
    try:
        return _read_frontmatter_stream(stream, strict=strict, source=path)
    except UnicodeDecodeError:
        return None, 0, 0


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
    with open(path, encoding="utf-8") as stream:
        return _read_frontmatter_file_stream(stream, path)


def fmf_split_frontmatter(content: str, strict: bool = True) -> tuple[str | None, int, int]:
    """
    The in-memory analog of `fmf_read_frontmatter_raw`: parse metadata frontmatter from a
    string rather than a file. Returns:

    - the metadata string (or None if no frontmatter is found)
    - the content offset (character position where the body begins, after the frontmatter)
    - the metadata start offset (character position where the metadata begins, 0 unless
      there are initial `#` lines before hash-style frontmatter)

    Offsets are character (Unicode code point) positions into `content`, so
    `content[:offset]` is the frontmatter region and `content[offset:]` is the body. This
    differs from the file-based `fmf_read_frontmatter_raw`, whose offsets are byte
    positions for file seeking. Does not parse the metadata or the body.

    Recognizes LF, CRLF, and CR line endings. The returned metadata preserves its original
    line endings, unlike the file API's universal-newline normalization.

    Returns `(None, 0, 0)` when there is no opening delimiter. When an opening delimiter is
    found but the closing one is missing, raises `FmFormatError` if `strict` is True
    (matching `fmf_read_frontmatter_raw`), or returns `(None, 0, 0)` if `strict` is False.
    This lets callers treat a bare leading delimiter as ordinary content, such as a
    Markdown `---` thematic break.
    """
    with StringIO(content, newline="") as stream:
        return _read_frontmatter_stream(stream, strict=strict)


def fmf_has_frontmatter(path: Path | str) -> bool:
    """
    Returns True if the file has frontmatter, False otherwise. Safe on binary files.

    An opening delimiter with no closing one, such as a Markdown `---` thematic break at
    the top of a file, is not frontmatter, so this returns False for it, where `fmf_read`
    raises `FmFormatError`. Frontmatter that holds no metadata, such as an empty block,
    is still frontmatter.
    """
    with open(path, encoding="utf-8") as stream:
        return _read_frontmatter_file_stream(stream, path, strict=False)[0] is not None


def _rewrite_frontmatter(
    path: Path | str, label: str, frontmatter_lines: list[str], fm_style: FmStyle | None
) -> None:
    """
    Atomically replace the file's frontmatter with `frontmatter_lines` (none, to strip it),
    keeping the body and any `#` lines before hash-style frontmatter. `fm_style` is the
    style of the new frontmatter, if there is any.
    """
    with atomic_write_text(path, label) as temp_file:
        with open(path, encoding="utf-8") as original_file:
            # Offsets from this stream, so they match the text copied from it.
            _, content_offset, metadata_start_offset = _read_frontmatter_file_stream(
                original_file, path
            )
            if metadata_start_offset > 0:
                if fm_style is not None and fm_style is not FmStyle.hash:
                    raise FmFormatError(
                        f"Cannot insert {fm_style.name}-style frontmatter after the `#` "
                        + f"lines before hash-style frontmatter: `{path}`"
                    )
                # Copy the `#` lines (a shebang, a PEP 723 block) that end where the
                # existing frontmatter starts.
                original_file.seek(0)
                while original_file.tell() != metadata_start_offset:
                    line = original_file.readline()
                    if not line:
                        break  # End of file: only if the file changed while being read.
                    temp_file.write(line)

            temp_file.writelines(frontmatter_lines)
            original_file.seek(content_offset)
            shutil.copyfileobj(original_file, temp_file)


def fmf_strip_frontmatter(path: Path | str) -> None:
    """
    Strip the metadata frontmatter from the file, in place on the file.
    Does not read the content (except to do a file copy) so should work fairly
    quickly on large files. Does nothing if there is no frontmatter.

    Keeps any `#` lines before hash-style frontmatter, such as a shebang or a PEP 723
    script block. Writes atomically and keeps the file's mode, as `fmf_write` does.
    """
    _, content_offset, _ = fmf_read_frontmatter_raw(path)
    if content_offset > 0:
        _rewrite_frontmatter(path, "strip", [], None)


def fmf_insert_frontmatter(
    path: Path | str,
    metadata: Metadata | None,
    fm_style: FmStyle = FmStyle.yaml,
    key_sort: KeySort[str] | None = None,
) -> None:
    """
    Insert metadata as frontmatter into the given file, inserting at the top
    and replacing any existing frontmatter.

    When existing hash-style frontmatter follows `#` lines, such as a shebang or a PEP 723
    script block, keeps those lines first and inserts the new frontmatter after them.
    Only hash-style frontmatter can follow them, so then raises `FmFormatError`, and
    leaves the file unchanged, if `fm_style` is another style. Writes atomically and keeps
    the file's mode, as `fmf_write` does.
    """
    # TODO: Add a flag (default on) to seek past # comments before inserting
    # frontmatter into a file that has none yet, for compatibility with shebangs and
    # `# /// script` inline dependencies.
    if not metadata:
        return

    if isinstance(metadata, str):
        frontmatter_str = metadata
    else:
        frontmatter_str = to_yaml_string(metadata, key_sort=key_sort)

    # Prepare the new frontmatter.
    frontmatter_lines = [fm_style.start + "\n"]
    if frontmatter_str:
        for line in _split_lines(frontmatter_str):
            frontmatter_lines.append(fm_style.prefix + line + "\n")
    frontmatter_lines.append(fm_style.end + "\n")

    _rewrite_frontmatter(path, "insert", frontmatter_lines, fm_style)
