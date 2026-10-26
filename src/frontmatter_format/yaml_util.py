"""
YAML file storage. Wraps ruamel.yaml with a few extra features and
convenience functions.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Iterable
from io import StringIO
from pathlib import Path
from typing import Any, Literal, TextIO, cast

import ruamel.yaml
import ruamel.yaml.main
from ruamel.yaml import YAML, Representer
from ruamel.yaml.composer import Composer
from ruamel.yaml.nodes import CollectionNode, MappingNode, ScalarNode
from ruamel.yaml.parser import Parser
from ruamel.yaml.representer import BaseRepresenter, RepresenterError

from ._atomic_write import atomic_write_text
from ._libyaml_guard import needs_pure_parser
from .key_sort import KeySort

YamlTyp = Literal["rt", "safe", "unsafe", "full", "base"]
"""
Valid values for ruamel.yaml YAML() typ parameter:
- "rt": Round-trip loader/dumper (preserves comments, formatting)
- "safe": Safe loader/dumper (recommended for untrusted input)
- "unsafe": Normal/unsafe loader/dumper (pending deprecation)
- "full": Full dumper including Python built-ins (potentially unsafe)
- "base": Base loader only
"""


class YamlSerializationError(RepresenterError):
    """Raised when a Python object graph cannot be serialized as configured."""


def none_or_empty_dict(val: Any) -> bool:
    return val is None or val == {}


_ESCAPE_ONLY_CHARACTERS = re.compile("[\x85\u2028\u2029\r]")
"""Characters only a double-quoted scalar keeps: NEL, LS, PS and CR.

ruamel writes them raw in every other style, and a reader then takes them as line breaks,
so the value reads back changed: a NEL folds to a space, a CRLF in a literal block becomes
LF, and a NEL in a literal block can make the document unreadable.
"""


class _EscapingRepresenter(BaseRepresenter):
    """
    Base for each `new_yaml` instance's own representer class: writes a scalar whose text
    holds a NEL, LS, PS or CR double-quoted, where ruamel escapes them (`\\N`, `\\L`,
    `\\P`, `\\r`), so it reads back exactly. Every other scalar is represented as ruamel
    would represent it, byte for byte.
    """

    def represent_scalar(  # pyright: ignore[reportImplicitOverride]
        self, tag: Any, value: Any, style: Any = None, anchor: Any = None
    ) -> ScalarNode:
        if style != '"' and isinstance(value, str) and _ESCAPE_ONLY_CHARACTERS.search(value):
            style = '"'
        return super().represent_scalar(tag, value, style=style, anchor=anchor)


YamlCustomizer = Callable[[YAML], None]

_default_yaml_customizers: list[YamlCustomizer] = []


def add_default_yaml_customizer(customizer: YamlCustomizer):
    """
    Add a function that configures every YAML instance `new_yaml` builds after this call.

    There is no single default instance: the customizers run inside each later `new_yaml`
    call, after the instance's own representers are registered. Representers and
    constructors a customizer registers through the instance (including with
    `register_class`) stay with that instance; ruamel's shared classes are not changed.
    """
    _default_yaml_customizers.append(customizer)


def add_default_yaml_representer(type: type[Any], represent: Callable[[Representer, Any], Any]):
    """
    Add a representer for a type to every YAML instance `new_yaml` builds after this call.

    This is the supported way to register a representer for every instance. A representer
    registered on one returned instance applies to that instance only.
    """
    _default_yaml_customizers.append(lambda yaml: yaml.representer.add_representer(type, represent))


def new_yaml(
    key_sort: KeySort[str] | None = None,
    suppress_vals: Callable[[Any], bool] | None = none_or_empty_dict,
    stringify_unknown: bool = False,
    typ: YamlTyp = "safe",
    allow_aliases: bool = False,
) -> YAML:
    """
    Configure a new YAML instance with custom settings.

    If just using this for pretty-printing values, can set `stringify_unknown` to avoid
    RepresenterError for unexpected types.

    For input, `typ="safe"` is safest. For output, consider using `typ="rt"` for better
    control of string formatting (e.g. style of long strings).

    Aliases are disabled by default so output is independent of shared Python object
    identity. Set `allow_aliases=True` to preserve aliases or serialize cyclic graphs.

    Representers and constructors registered on the returned instance, including through
    `register_class`, apply to that instance only, and ruamel's shared classes are left
    unchanged. Use `add_default_yaml_representer` or `add_default_yaml_customizer` to
    reach every instance built afterwards.

    A string that holds a NEL, LS, PS or CR is always written double-quoted, with the
    escapes `\\N`, `\\L`, `\\P` and `\\r`, whatever style was asked for: in any other
    style ruamel writes those characters raw and they read back as line breaks. Every other
    string is written as ruamel writes it.

    The instance always uses ruamel's pure-Python parser and emitter, even when ruamel's
    optional C extension is installed, so its reading and its output bytes do not depend
    on what else is installed. `from_yaml_string`, `read_yaml_file` and the frontmatter
    readers use the C parser where it reads exactly as this instance does; see
    `yaml_parser_mode`.
    """
    yaml = YAML(typ=typ, pure=True)
    # ruamel's `add_representer` and `add_constructor` are classmethods on the representer
    # and constructor classes every instance of a `typ` shares, so registering this
    # instance's representers there would rewrite every other instance's output, including
    # mid-dump on another thread, and a constructor a customizer registers would reach every
    # loader in the process. A private subclass of each keeps them with this instance;
    # ruamel builds the representer and constructor from these lazily. (`typ="full"` has
    # no constructor: it is for dumping only.) The representer subclass also escapes the
    # characters only a double-quoted scalar keeps (`_EscapingRepresenter`).
    yaml.Representer = type(yaml.Representer.__name__, (_EscapingRepresenter, yaml.Representer), {})
    if yaml.Constructor is not None:
        yaml.Constructor = type(yaml.Constructor.__name__, (yaml.Constructor,), {})
    yaml.default_flow_style = False  # Block style dictionaries.

    suppr = suppress_vals or (lambda v: False)

    # Ignore None values in output. Sort keys if key_sort is provided.
    def represent_dict(dumper, data: Any):  # pyright: ignore
        if key_sort:
            data = {k: data[k] for k in sorted(data.keys(), key=key_sort)}
        return dumper.represent_dict({k: v for k, v in data.items() if not suppr(v)})

    yaml.representer.add_representer(dict, represent_dict)

    # Use YAML block style for strings with newlines.
    def represent_str(dumper, data):  # pyright: ignore
        style = "|" if "\n" in data else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

    yaml.representer.add_representer(str, represent_str)

    # Customize the YAML instance.
    for customizer in _default_yaml_customizers:
        customizer(yaml)

    if stringify_unknown:

        def represent_unknown(dumper, data: Any):  # pyright: ignore
            return dumper.represent_str(str(data))

        yaml.representer.add_representer(None, represent_unknown)

    if key_sort:
        yaml.representer.sort_base_mapping_type_on_output = False

    if not allow_aliases:
        representer = yaml.representer
        original_represent_data = representer.represent_data
        active_object_ids: set[int] = set()

        def represent_data(data: Any) -> Any:
            object_id = id(data)
            if object_id in active_object_ids:
                raise YamlSerializationError(
                    "Cannot serialize a cyclic object graph with aliases disabled; "
                    + "use allow_aliases=True in a low-level YAML writer if aliases are intentional."
                )

            active_object_ids.add(object_id)
            try:
                return original_represent_data(data)
            finally:
                active_object_ids.remove(object_id)

        representer.ignore_aliases = lambda *_args: True
        representer.represent_data = represent_data

    return yaml


PURE_YAML_ENV = "FRONTMATTER_FORMAT_PURE_YAML"
"""
Environment variable that, set to anything but empty or `0`, turns off the C parser.

For diagnosis: results are meant to be the same either way (see the build gate,
`CHECKED_LIBYAML_VERSION`), so this changes only speed and what `yaml_parser_mode` reports.
It is read on every load, so setting it in-process works too.
"""

_CParser: Any = getattr(ruamel.yaml.main, "CParser", None)
"""ruamel's libyaml parser class if its C extension was importable, otherwise None.

Taken from `ruamel.yaml.main` so that it is the very object ruamel compares a YAML
instance's `Parser` with when it picks its C loading path.
"""

CHECKED_C_PARSER_MODULES = ("ruamel.yaml.clib._ruamel_yaml", "_ruamel_yaml")
"""The modules `ruamel.yaml.clib` defines its C parser in, the only C parser the guards
were searched against.

`CParser.__module__` is `ruamel.yaml.clib._ruamel_yaml` on recent clib releases and
`_ruamel_yaml` on older ones. `ruamel.yaml.clibz` builds the same libyaml sources with
Zig and a free-threading flag into `_ruamel_yaml_clibz` and reports the same
`CHECKED_LIBYAML_VERSION`, so only the parser's module tells the two apart. No ruamel
release yet hands clibz's parser to `YAML()`, but one that did would otherwise put the
readers on a build the search never covered, so a parser from any other module keeps them
pure.
"""

CHECKED_LIBYAML_VERSION = "0.1.7"
"""The libyaml build, as `ruamel.yaml.clib` reports it, that the guards were derived for.

The guards in `_libyaml_guard` are empirical: they list the shapes on which this libyaml
accepts what pure ruamel rejects, or reads a different value. Another libyaml build could
add a shape, so the C parser is used only when it is clib's (`CHECKED_C_PARSER_MODULES`),
reports this build, and runs on a checked ruamel release (`CHECKED_RUAMEL_VERSIONS`), and
`yaml_parser_mode` reports `"pure"` otherwise. Every `ruamel.yaml.clib` release so far
reports this string, so a new clib release needs `devtools/yaml_parser_fuzz.py` rerun even
when the string is unchanged. Widen any of these constants only after rerunning that
search and `tests/test_c_parser.py` on the new build. softschema gates its own copy of the
guards on the same values.
"""

CHECKED_RUAMEL_VERSIONS = ((0, 18), (0, 20))
"""The ruamel.yaml releases the guards were searched against: from the first (inclusive)
to the second (exclusive), as `(major, minor)`.

The pure parser is the reference the guards compare libyaml with, so it moves too: a
ruamel release that changes what pure ruamel accepts changes which texts need a guard.
"""


def _ruamel_is_checked(version: tuple[int, ...] = ruamel.yaml.version_info) -> bool:
    """Whether `version` of ruamel.yaml is inside `CHECKED_RUAMEL_VERSIONS`."""
    lower, upper = CHECKED_RUAMEL_VERSIONS
    return lower <= tuple(version[:2]) < upper


def _clib_module() -> Any:
    """The `ruamel.yaml.clib` module that defines ruamel's C parser, or None when ruamel has
    no C parser or its parser comes from anywhere else (`CHECKED_C_PARSER_MODULES`).

    ruamel itself imports `_ruamel_yaml`, so that name is the fallback when the qualified
    one is not registered. Either module counts only if it holds this very parser class, so
    the version read from it is the parser's own.
    """
    name = getattr(_CParser, "__module__", None)
    if _CParser is None or name not in CHECKED_C_PARSER_MODULES:
        return None
    for candidate in (name, "_ruamel_yaml"):
        module = sys.modules.get(candidate)
        if getattr(module, "CParser", None) is _CParser:
            return module
    return None


def _installed_libyaml_version() -> str | None:
    """The libyaml version `ruamel.yaml.clib`'s C parser reports, or None when ruamel has no
    C parser or its parser is not clib's (see `_clib_module`)."""
    get_version_string = getattr(_clib_module(), "get_version_string", None)
    version = get_version_string() if callable(get_version_string) else None
    return version if isinstance(version, str) else None


def _c_parser_is_checked() -> bool:
    """Whether ruamel's C parser is clib's, and it is the build the guards were derived for
    on a checked ruamel release."""
    return _installed_libyaml_version() == CHECKED_LIBYAML_VERSION and _ruamel_is_checked()


_C_PARSER_CHECKED: bool = _c_parser_is_checked()
"""Whether the readers may use the C parser at all, decided once at import."""

_C_MAX_DEPTH = 100
"""Deepest nesting of collection nodes for which a C reading is kept.

Pure ruamel composes nodes recursively and raises `RecursionError` at about 490 levels
under Python's default recursion limit, where libyaml reads on. The check runs on the
document libyaml composed, before anything is constructed from it (see
`_checked_constructor`), so a tag constructor cannot hide depth inside an object that is
not a container. Deeper documents are read again by pure ruamel, which then returns or
raises whatever it does at the caller's depth.
"""

_C_SCAN_DEPTH = 150
"""Nesting the text may reach, by a cheap upper bound, beyond which it skips the C parser.

ruamel's C composer recurses on the C stack, about 300 bytes per level, and a stack
overflow there is a segfault on CPython 3.10 to 3.13 (3.14 turns it into
`RecursionError`), before any node exists to check against `_C_MAX_DEPTH`. It overflows at
about 30,000 levels on an 8 MB main-thread stack, at about 400 on a 128 KB thread stack,
which is the default on musl-based images such as `python:*-alpine` and a common setting
for worker threads, and at 165 to 201 levels on a 64 KB thread (3.10 to 3.13; on 3.14,
whose frames are larger, the composer gives a clean `RecursionError` at 74 levels, which the
C attempt turns into a pure re-read). A document whose shape allows more than this many
levels (see `_nesting_bound`) is read by pure ruamel instead, which raises `RecursionError`
where it cannot compose. 150 leaves a 64 KB thread, the smallest a program is likely to set,
some margin on every CPython that can segfault; threads under that (CPython allows 32 KB)
are outside this bound's assumption, and pure ruamel on 3.10 does not survive them either.
Any document that really nests past `_C_MAX_DEPTH` ends with pure ruamel anyway, so the
bound costs speed only on a document with more than 150 flow collections in all, or
indented 75 columns.
"""

_FLOW_OPEN = re.compile(r"[\[{](?<![^ \t\r\n\[{,:?][\[{])")
"""A `[` or `{` where libyaml can open a flow collection: at the start of the text or
after whitespace, another flow indicator, a colon or a `?`.

Anywhere else, such as inside a plain scalar (`a[b`) or right after a quote, a tag, an
anchor or a closing bracket, libyaml either reads it as content or rejects the text, so
the count is an upper bound on the flow nesting depth.

This regex and the two below start with a literal character, as the guards in
`_libyaml_guard` do, so the engine can skip to the next candidate instead of trying a
lookbehind or a group at every position. Each matches exactly what its earlier
lookbehind-first form matched; `tests/test_c_parser.py` compares the two.
"""

_INDICATOR_CHAIN = re.compile(r"[-?] +(?:[-?] +)*")
"""A run of `- ` and `? ` indicators on one line, each of which opens a block collection."""

_LINE_INDENT = re.compile(r" (?<![^\r\n] ) *")
"""The spaces that indent a line."""


def _nesting_bound(text: str) -> int:
    """
    A cheap upper bound on how deep the document in `text` can nest collections.

    Flow collections need an opener each (`_FLOW_OPEN`). Block collections are opened on
    one line by a chain of indicators (`- - - x`) or on a new line by indentation; every
    level opened by indentation costs at least one more column, except a sequence written
    at its parent key's indentation, so one column opens at most two levels.
    """
    flow = len(_FLOW_OPEN.findall(text))
    chain = max(
        (run.count("-") + run.count("?") for run in _INDICATOR_CHAIN.findall(text)), default=0
    )
    indent = max((len(run) for run in _LINE_INDENT.findall(text)), default=0)
    return flow + chain + 2 * indent + 2


_LOADER_ATTRS = ("_reader", "_scanner", "_parser", "_composer", "_constructor", "_resolver")


def yaml_parser_mode() -> Literal["c-first", "pure"]:
    """
    Which ruamel parser `from_yaml_string`, `read_yaml_file` and the frontmatter readers
    use in this process.

    `"c-first"` means ruamel's C extension (`ruamel.yaml.clib`) is installed, ruamel's
    `YAML()` uses its parser, it is the libyaml build the guards were checked against on a
    checked ruamel release (`CHECKED_C_PARSER_MODULES`, `CHECKED_LIBYAML_VERSION`,
    `CHECKED_RUAMEL_VERSIONS`), and it is not turned off with
    `FRONTMATTER_FORMAT_PURE_YAML`: libyaml reads each text that has none of the shapes on
    which it was found to differ from pure ruamel, and pure ruamel reads the rest and every
    text libyaml fails on. `"pure"` means every text is read by pure ruamel: the extension
    is absent, is another build or release, is turned off, or a default customizer has
    replaced or configured the loader in a way ruamel's C loader would bypass (see
    `_accepts_c_parser`). `ruamel.yaml.clibz` (ruamel.yaml's `libyaml` extra) is never used:
    it is another build the guards were not searched against, so a ruamel release whose
    `YAML()` took its parser would read pure here. The build check happens once at import;
    the environment variable and the customizers are consulted on every call, which builds
    one instance with `new_yaml()`. Results are meant to be the same in both modes, with
    only speed differing; the guards that make that so rest on a differential search, which
    is why the build gate exists.
    """
    return "c-first" if _c_parser_active() and _accepts_c_parser(new_yaml()) else "pure"


def _c_parser_active() -> bool:
    return (
        _CParser is not None
        and _C_PARSER_CHECKED
        and os.environ.get(PURE_YAML_ENV, "") in ("", "0")
    )


def _load_yaml_text(text: Any) -> Any:
    """
    Load one YAML document exactly as pure ruamel reads it with `new_yaml()`.

    With the C extension active, a text `_c_eligible` clears is read by libyaml first. If
    that attempt raises anything at all, or composes a document pure ruamel might not read
    the same way, the text is read again by pure ruamel, with the same instance, and
    whatever that returns or raises is the result. Bytes and streams, which ruamel also
    reads, go to pure ruamel directly.

    Two visible differences remain on the C path, neither of which changes a value: a
    constructor a customizer registered that raises on the C attempt runs again on the pure
    re-read, so its side effects happen twice; and a warning issued during a kept C reading
    carries libyaml's marks, which have no source snippet. The default configuration issues
    no constructor warnings; an instance set to warn on duplicate keys stays on pure ruamel
    (`_accepts_c_parser`).
    """
    yaml = new_yaml()
    if _c_parser_active() and _accepts_c_parser(yaml) and _c_eligible(text):
        value = _load_with_c(yaml, text)
        if value is not _C_FAILED:
            return value
    return _load_pure(yaml, text)


def _c_eligible(text: Any) -> bool:
    """
    Whether `text` may be given to libyaml: a `str` without any shape from
    `needs_pure_parser` whose shape cannot nest past `_C_SCAN_DEPTH`. The one routing
    predicate, shared with the differential search in `devtools/yaml_parser_fuzz.py`.
    """
    return (
        isinstance(text, str) and not needs_pure_parser(text) and _nests_within(text, _C_SCAN_DEPTH)
    )


def _nests_within(text: str, limit: int) -> bool:
    """
    Whether `_nesting_bound(text) <= limit`, deciding most texts from character counts.

    `rough` counts every `[`, `{`, `-` and `?` plus the bound's constant 2, so it is at
    least the flow and chain terms plus 2, which count some of those characters. If
    `spare = limit - rough` is not negative and no run of `spare // 2 + 1` spaces occurs,
    no indent is longer than `spare // 2`, so the indent term (twice the indent) is at most
    `spare` and the bound at most `limit`. Otherwise the exact bound decides, so the answer
    is always the exact one.
    """
    rough = text.count("[") + text.count("{") + text.count("-") + text.count("?") + 2
    spare = limit - rough
    if spare >= 0 and " " * (spare // 2 + 1) not in text:
        return True
    return _nesting_bound(text) <= limit


_C_FAILED: Any = object()
"""What `_load_with_c` returns when the C reading cannot be used."""


def _load_with_c(yaml: YAML, text: str) -> Any:
    """
    libyaml's reading of `text` through `yaml`, an instance `_accepts_c_parser` cleared, or
    `_C_FAILED`. Either way `yaml` is left as it was, ready for a pure reading: ruamel's C
    loading path hangs its combined loader and the stream on the instance, and the pure
    path would pick that loader up as its scanner.

    The instance's constructor is wrapped for the attempt (`_checked_constructor`), so the
    document libyaml composes is checked for depth and sharing before anything is
    constructed from it.
    """
    before = set(vars(yaml))
    constructor = yaml.Constructor
    yaml.Parser = _CParser
    yaml.Constructor = _checked_constructor(constructor)
    try:
        return yaml.load(text)
    except Exception:
        return _C_FAILED
    finally:
        yaml.Parser = Parser
        yaml.Constructor = constructor
        for attr in set(vars(yaml)) - before:
            delattr(yaml, attr)


class _CReadingDiscarded(Exception):
    """Raised inside a C attempt whose composed document is one pure ruamel may not read the
    same way: nested past `_C_MAX_DEPTH`, or reaching one collection node twice."""


def _checked_constructor(base: type) -> type:
    """
    A subclass of the constructor class `base` whose `construct_document` first checks the
    composed document with `_node_nested_deeper_than`.

    ruamel's C loader derives its combined loader from the instance's `Constructor` and
    calls `construct_document` with the root node libyaml composed, so this is the one
    point between composing and constructing on that path. Checking nodes rather than the
    constructed value means a constructor a customizer registered for a tag cannot hide a
    deep document inside an object that is not a container (Qodo's `!box` case).
    """

    def construct_document(self: Any, node: Any) -> Any:
        if _node_nested_deeper_than(node, _C_MAX_DEPTH):
            raise _CReadingDiscarded
        return base.construct_document(self, node)  # pyright: ignore[reportAttributeAccessIssue]

    return type(base.__name__, (base,), {"construct_document": construct_document})


def _load_pure(yaml: YAML, text: Any) -> Any:
    return yaml.load(text)


def _accepts_c_parser(yaml: YAML) -> bool:
    """
    Whether swapping in the C parser leaves everything else about loading as configured.

    ruamel's C loader replaces the reader, scanner, parser and composer and builds its own
    constructor and resolver objects, so a customizer that replaced or configured any of
    those, or set a version or a depth limit, keeps the pure parser. So does an instance set
    to warn on duplicate keys (`allow_duplicate_keys = None`): the warning's marks come from
    the parser, and libyaml's have no source snippet. The attributes are read with
    defaults because they differ between ruamel releases: 0.18 has no `max_depth`.
    """
    return (
        yaml.Parser is Parser
        and yaml.Composer is Composer
        and yaml.Constructor is not None
        and getattr(yaml, "allow_duplicate_keys", False) is not None
        and yaml.Reader is None
        and yaml.Scanner is None
        and getattr(yaml, "version", None) is None
        and not getattr(yaml, "max_depth", 0)
        and not any(hasattr(yaml, attr) for attr in _LOADER_ATTRS)
    )


def _node_nested_deeper_than(node: Any, limit: int) -> bool:
    """
    Whether the composed document `node` nests collection nodes more than `limit` deep, or
    reaches one collection node twice, as an alias does. Either sends the text back to pure
    ruamel.

    Both composers hand an alias the very node object its anchor produced, so sharing is a
    repeated node. Every node object is distinct otherwise, so two empty sequences are two
    nodes, where the constructed values could be CPython's one shared empty tuple.
    """
    if not isinstance(node, CollectionNode):
        return False
    seen: set[int] = set()
    level: list[CollectionNode] = [node]
    depth = 1
    while level:
        if depth > limit:
            return True
        below: list[CollectionNode] = []
        for current in level:
            if id(current) in seen:
                return True
            seen.add(id(current))
            children: Iterable[Any]
            if isinstance(current, MappingNode):
                pairs = cast(Iterable[tuple[Any, Any]], current.value)
                children = (part for pair in pairs for part in pair)
            else:
                children = cast(Iterable[Any], current.value)
            below += [child for child in children if isinstance(child, CollectionNode)]
        level = below
        depth += 1
    return False


def from_yaml_string(yaml_string: str) -> Any:
    """
    Read a YAML string into a Python object, as `new_yaml().load()` reads it.
    """
    return _load_yaml_text(yaml_string)


def read_yaml_file(path: str | Path) -> Any:
    """
    Read YAML file into a Python object, as `new_yaml().load()` reads its text.
    """
    path = Path(path)
    return _load_yaml_text(path.read_text(encoding="utf-8"))


def to_yaml_string(
    value: Any,
    key_sort: KeySort[str] | None = None,
    stringify_unknown: bool = False,
    typ: YamlTyp = "rt",
    allow_aliases: bool = False,
) -> str:
    """
    Convert a Python object to a YAML string.
    """
    stream = StringIO()
    new_yaml(
        key_sort=key_sort,
        stringify_unknown=stringify_unknown,
        typ=typ,
        allow_aliases=allow_aliases,
    ).dump(value, stream)
    return stream.getvalue()


def dump_yaml(
    value: Any,
    stream: TextIO,
    key_sort: KeySort[str] | None = None,
    stringify_unknown: bool = False,
    typ: YamlTyp = "rt",
    allow_aliases: bool = False,
) -> None:
    """
    Write a Python object to a YAML stream.
    """
    new_yaml(
        key_sort=key_sort,
        stringify_unknown=stringify_unknown,
        typ=typ,
        allow_aliases=allow_aliases,
    ).dump(value, stream)


def write_yaml_file(
    value: Any,
    path: str | Path,
    key_sort: KeySort[str] | None = None,
    stringify_unknown: bool = False,
    typ: YamlTyp = "rt",
    allow_aliases: bool = False,
) -> None:
    """
    Write the given value to the YAML file, creating it atomically.

    Writes through a uniquely named temp file in the same directory, as the frontmatter
    writers do. A file that is replaced keeps its mode where the filesystem allows it; a new
    file gets the default mode (0o666 less the umask).
    """
    text = to_yaml_string(
        value,
        key_sort,
        stringify_unknown=stringify_unknown,
        typ=typ,
        allow_aliases=allow_aliases,
    )
    with atomic_write_text(path, "yaml") as stream:
        stream.write(text)
