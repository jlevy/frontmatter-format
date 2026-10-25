"""
Texts that must not be read by libyaml, because it could read them differently from pure
ruamel.yaml without raising.

With ruamel's optional C extension (`ruamel.yaml.clib`) installed, the readers in
`yaml_util` scan and parse with libyaml, a YAML 1.1 scanner, while construction and
resolution stay in ruamel's Python code. When libyaml raises, the text is read again by
pure ruamel, so texts libyaml *rejects* need no guard. These guards cover the other
direction, which no fallback can see: libyaml accepting a text pure ruamel rejects, or
reading it to a different value. Each family was found by comparing the two parsers over
generated and mutated documents through this library's own loader, and each is pinned
by a test in `tests/test_c_parser.py`.

Every check is a substring test or a search that starts at a literal character, so the
guard costs a small fraction of a C parse.
"""

from __future__ import annotations

import re

_PURE_ONLY_CHARACTERS = ("\t", "\x85", "\u2028", "\u2029", "\ufeff")
"""Tab, NEL, LS, PS and a byte order mark.

libyaml skips a tab between block tokens (after a value, a colon or `]`) where pure ruamel
refuses it, and telling those tabs from harmless ones would take a scanner. NEL, LS and
PS are line breaks to libyaml (YAML 1.1) and mostly content to pure ruamel (YAML 1.2), so
`-<NEL>-` is two entries to one and a nested sequence to the other. libyaml skips a byte
order mark at the start of any line, where pure ruamel skips one only at the start of
the text.
"""

_DIRECTIVE_LINE = re.compile(r"%(?<![^\r\n]%)")
"""A `%` at the start of the text or of a line, where a directive can be.

libyaml ignores `%YAML 1.1` when values are resolved, so `yes` stays a string and `017`
reads as seventeen, where pure ruamel reads `True` and fifteen.
"""

_DOCUMENT_END_LINE = re.compile(r"\.\.\.(?<![^\r\n]\.\.\.)(?=[ \r\n]|\Z)")
"""A line that is a `...` document end marker.

libyaml skips a second marker where pure ruamel starts another document and refuses the
stream.
"""

_BLOCK_HEADER_COMMENT = re.compile(r"#(?:(?<=[|>]#)|(?<=[|>][-+0-9]#)|(?<=[|>][-+0-9]{2}#))")
"""A block scalar header with a comment and no space before it, such as `|#`.

Pure ruamel rejects it; libyaml reads the comment.
"""

_BLOCK_SPACE_LINE = re.compile(r"[|>][-+0-9]*(?: +#[^\r\n]*| *)(?:\r\n?|\n) +(?:\r\n?|\n)")
"""A block scalar header followed by a line of only spaces.

When such a line has fewer spaces than a later leading line, pure ruamel reports "more
indented follow up line than first in a block scalar"; libyaml reads the scalar.
"""

_ROOT_BLOCK_SCALAR = re.compile(
    r"(?:[ \r\n]|#[^\r\n]*|(?:---|\.\.\.)(?=[ \r\n]|\Z))*(?:[!&][^ \r\n]*[ ]+)*[|>]"
)
"""A document that may be a block scalar, after any blank lines, comments and markers.

Its content may start at column zero, where libyaml reads a `#` line as a comment and pure
ruamel reads it as content.
"""

_SPACED_COLON = re.compile(r":(?<=[ \"']:)(?![ \r\n])")
"""A colon after a space or quote and before anything but a space or line break."""


def _has_quoted_key_colon(text: str) -> bool:
    """
    Whether a quoted scalar, then any spaces, then a colon not followed by a space or line
    break appears in `text`.

    In a flow sequence such as `["a":1]`, libyaml reads the colon as a mapping indicator and
    pure ruamel, following YAML 1.2, refuses the text. The search visits each such colon
    and looks back over spaces for the closing quote.
    """
    for match in _SPACED_COLON.finditer(text):
        i = match.start() - 1
        while i >= 0 and text[i] == " ":
            i -= 1
        if i >= 0 and text[i] in "\"'":
            return True
    return False


_FLOW_EXPLICIT_KEY = re.compile(r"\?(?<![^\[{, \r\n]\?)")
"""A `?` at the start of the text or after a space, line break, `[`, `{` or `,`, checked
in texts with a flow collection.

Inside a flow collection libyaml (YAML 1.1) always reads such a `?` as an explicit key
indicator and pairs it differently from pure ruamel (YAML 1.2): `[? :]` and `[?&a :]` have
a null key in libyaml and the key `":"` in pure ruamel, and an empty explicit key makes
libyaml take the next `]` as the end of the pair, so it reads `[? ]]`, which pure ruamel
refuses.
"""

_FLOW_TOKEN_COLON = re.compile(r":(?<=[ \[{,\r\n]:)(?![ \r\n])")
"""A colon at the start of a token and before anything but a space or line break, checked
in texts with a flow collection.

Inside a flow collection libyaml always reads such a colon as a value indicator; pure ruamel
reads it as a value indicator only after a key, and otherwise as the start of a plain
scalar. So `[&a :]` is `[":"]` to pure ruamel and a list holding one empty pair to libyaml.
"""

_ANCHOR_NAME_END = re.compile(r"[&*](?<![^ \r\n\[{,?:-][&*])[0-9A-Za-z_-]+[?:%@`]")
"""An anchor or alias, at the start of a token, whose name runs into `?`, `:`, `%`, `@` or a
backtick.

libyaml ends an anchor name at the first character outside `[0-9A-Za-z_-]` and accepts
these five as the next token, so `&a: 1` is an anchored empty key to it; pure ruamel takes
them as part of the name, so `&a: 1` is the integer 1 anchored as `a:`.
"""

_EMPTY_NON_SPECIFIC_TAG = re.compile(r"!(?<![^ \r\n\[{,?:-]!)(?=[ \r\n,\]}]|\Z)")
"""A non-specific tag `!` written alone, before a space, line break or flow indicator.

On an empty node, libyaml's event leaves the node an empty string and pure ruamel's leaves
it null, so `k: !` reads `''` in one and `None` in the other.
"""


def needs_pure_parser(text: str) -> bool:
    """
    Whether `text` has a shape on which libyaml may accept what pure ruamel rejects, or read
    it to a different value. Such texts are read by pure ruamel directly.
    """
    if not text.isascii():
        if any(char in text for char in _PURE_ONLY_CHARACTERS):
            return True
    elif "\t" in text:
        return True
    if "%" in text and _DIRECTIVE_LINE.search(text) is not None:
        return True
    if "..." in text and _DOCUMENT_END_LINE.search(text) is not None:
        return True
    if "#" in text and _BLOCK_HEADER_COMMENT.search(text) is not None:
        return True
    if (" \n" in text or " \r" in text) and _BLOCK_SPACE_LINE.search(text) is not None:
        return True
    if _has_quoted_key_colon(text):
        return True
    if "[" in text or "{" in text:
        if "?" in text and _FLOW_EXPLICIT_KEY.search(text) is not None:
            return True
        if ":" in text and _FLOW_TOKEN_COLON.search(text) is not None:
            return True
    if ("&" in text or "*" in text) and _ANCHOR_NAME_END.search(text) is not None:
        return True
    if "!" in text and _EMPTY_NON_SPECIFIC_TAG.search(text) is not None:
        return True
    return _ROOT_BLOCK_SCALAR.match(text) is not None
