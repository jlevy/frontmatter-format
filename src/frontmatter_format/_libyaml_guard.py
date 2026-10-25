"""
Texts that must not be read by libyaml, because it could read them differently from pure
ruamel.yaml without raising.

With ruamel's optional C extension (`ruamel.yaml.clib`) installed, the readers in
`yaml_util` scan and parse with libyaml, a YAML 1.1 scanner, while construction and
resolution stay in ruamel's Python code. When libyaml raises, the text is read again by
pure ruamel, so texts libyaml *rejects* need no guard. These guards cover the other
direction, which no fallback can see: libyaml accepting a text pure ruamel rejects, or
reading it to a different value. Each family was found by comparing the two parsers over
generated and mutated documents through this library's own loader
(`devtools/yaml_parser_fuzz.py` is that search), and each is pinned by a test in
`tests/test_c_parser.py`.

Every check is a substring test or a single pass over the text. The regexes start at a
literal character and skip ahead between candidates, and none of them can match a
stretch of text in more than one way, so Python's backtracking engine never retries a
split: the cost is linear in the text, and `tests/test_c_parser.py` pins bounded time and
linear growth on adversarial inputs (a long `#` banner, hundreds of comment lines with
trailing spaces, a line of thousands of `| #`, a block scalar with tens of thousands of
space-only lines). Python 3.10, which this package supports, has no possessive
quantifiers or atomic groups, so unambiguity comes from lookarounds and from searching
each candidate line separately instead.

softschema (`softschema/_portable.py`) carries the same guards for its own reader. The
two agree on every shared family: the tab, NEL/LS/PS/BOM, `%` directive line, `...`
line, `|#` header, space-line, root block scalar and quoted-colon rules are the same
rules (softschema writes them with Python 3.11 possessive quantifiers). This module has
three more rules because this loader keeps tags, anchors, aliases and non-string keys,
which softschema's preflight and value check reject on both paths: every node property
or alias (`!`, `&` or `*` at the start of a token) is routed here, as is a flow `?` and a
colon at the start of a token or after a flow collection. softschema alone routes a colon
after a space in block context (`a: x :y`), which libyaml rejects, so here the fallback
covers it. Any new family found in one must be ported to the other.
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

Pure ruamel rejects it; libyaml reads the comment. A header has at most two indicator
characters; libyaml rejects a longer one too.
"""

_SPACE_ONLY_LINE = re.compile(r"(?:\r\n?|\n)( +)(?=[\r\n])")
"""A line of only spaces, which is where a block scalar can read differently (below).

The search finds these lines first and then looks at the line before each one. Such lines
are not rare: an editor that keeps indentation on blank lines writes one for every blank
line inside a literal block, so the work per line has to stay constant
(see `_block_scalar_before_space_line`).
"""

_BLOCK_HEADER_AT_LINE_END = re.compile(r"[|>][-+0-9]{0,2}(?: +#| *\Z)")
"""A block scalar header ending a line: `|` or `>`, up to two indicator characters, then
only spaces, or a space and a comment. Searched within one line, so `\\Z` is its end.

Each `|` or `>` costs only the spaces after it, never the rest of the line, which keeps a
line full of `| #` linear.
"""


def _block_scalar_before_space_line(text: str) -> bool:
    """
    Whether a block scalar header is followed by a line of only spaces.

    When such a line has fewer spaces than a later leading line, pure ruamel reports "more
    indented follow up line than first in a block scalar"; libyaml reads the scalar.

    The backward search for the start of the line before each match is bounded below by the
    start of the previous match, the line break that ended the line before it, so each
    space-only line costs the length of the one line before it. Searching from 0 instead
    made the whole text quadratic in the number of space-only lines: in an LF-only text
    the search for `\\r` found nothing and scanned back to the start every time. Bounding
    at the previous match's *end* has the same effect on consecutive space-only lines (the
    next match starts exactly there, so the bounded search finds no break and falls back
    to 0), and also let a header several lines up count as the line before.
    """
    low = 0
    for match in _SPACE_ONLY_LINE.finditer(text):
        line_end = match.start()
        line_start = max(text.rfind("\n", low, line_end), text.rfind("\r", low, line_end)) + 1
        if _BLOCK_HEADER_AT_LINE_END.search(text, line_start, line_end) is not None:
            return True
        low = line_end
    return False


_ROOT_BLOCK_SCALAR = re.compile(
    r"(?:[ \r\n]|#[^\r\n]*(?![^\r\n])|(?:---|\.\.\.)(?=[ \r\n]|\Z))*[|>]"
)
"""A document that may be a block scalar, after any blank lines, comments and markers.

Its content may start at column zero, where libyaml reads a `#` line as a comment and pure
ruamel reads it as content. A block scalar with a tag or anchor before it, on the same line
or an earlier one, is routed by `_NODE_PROPERTY` before this rule is reached.

The lookahead after a comment, `(?![^\\r\\n])`, lets it end only at a line break, so the
repetition has exactly one way to consume each line. Without it, the engine could stop a
comment at any `#` or space and, on an ordinary document, tried every split before
failing, doubling the cost with each `#` of a leading banner comment. One consequence: a
`|` or `>` inside a comment is part of the comment, as it should be, and no longer routes
the text to pure ruamel.
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

_FLOW_TOKEN_COLON = re.compile(r":(?<=[ \[{,\r\n\]}]:)(?![ \r\n])")
"""A colon at the start of a token, or right after a flow collection, and before anything
but a space or line break, checked in texts with a flow collection.

Inside a flow collection libyaml always reads such a colon as a value indicator; pure ruamel
reads it as a value indicator only after a key, and otherwise as the start of a plain
scalar. So `[&a :]` is `[":"]` to pure ruamel and a list holding one empty pair to libyaml.
After a flow collection the colon makes libyaml read a single-pair mapping with a tuple
key, where pure ruamel expects `,` or `]`: `[[]:]` is `[{(): None}]` to libyaml and a
`ParserError` to pure ruamel, and so are `k: [[a]:b]` and `[a, []:x]`.
"""

_NODE_PROPERTY = re.compile(r"[!&*](?<![^ \t\r\n\[{,\]}?-][!&*])")
"""A tag (`!`), anchor (`&`) or alias (`*`) indicator at the start of a token: at the start
of the text or after whitespace, a flow indicator, `?` or `-`. Anywhere else these
characters are content to both parsers (`Tom&Jerry`, `a*b`, `Hello!`).

Every text with a node property or alias is read by pure ruamel. Three families were found
one at a time where a property meets what follows it, and each was a silent difference the
fallback cannot see: libyaml ends an anchor name at the first character outside
`[0-9A-Za-z_-]`, so `&a: 1` is an anchored empty key to it and the integer 1 anchored as
`a:` to pure ruamel; on an empty node the non-specific tag, written `!` or `!<!>`, is an
empty string to libyaml and null to pure ruamel (`k: !`, `k: !<!>`); and a root block
scalar whose tag or anchor sits on an earlier line (`--- !!str\n|\n#x\n`) has its
column-zero `#` line read as a comment by libyaml and as content by pure ruamel. Routing
the whole class closes the shapes not yet found as well. Frontmatter rarely carries
properties (4 of 140 real frontmatter blocks and YAML files sampled did, all GitHub
workflow files with `&&`, `'* *'` or `"*.ts"` after a space), so the cost is small, and an
alias always went back to pure ruamel anyway, because a shared node discards the C reading.
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
    if (" \n" in text or " \r" in text) and _block_scalar_before_space_line(text):
        return True
    if _has_quoted_key_colon(text):
        return True
    if "[" in text or "{" in text:
        if "?" in text and _FLOW_EXPLICIT_KEY.search(text) is not None:
            return True
        if ":" in text and _FLOW_TOKEN_COLON.search(text) is not None:
            return True
    if ("!" in text or "&" in text or "*" in text) and _NODE_PROPERTY.search(text) is not None:
        return True
    return _ROOT_BLOCK_SCALAR.match(text) is not None
