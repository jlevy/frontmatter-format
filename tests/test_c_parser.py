"""
Reading YAML with ruamel's optional C extension gives exactly pure ruamel's results.

Tests marked `requires_c` need `ruamel.yaml.clib` (the `_ruamel_yaml` module) and skip
without it. The others simulate the extension or do not need it.
"""

from __future__ import annotations

import ast
import itertools
import json
import math
import os
import random
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Any, cast

import pytest
import ruamel.yaml.error
import ruamel.yaml.main
from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.emitter import Emitter, RoundTripEmitter
from ruamel.yaml.parser import Parser, RoundTripParser

from frontmatter_format import (
    _libyaml_guard,
    fmf_read,
    fmf_read_frontmatter,
    fmf_read_frontmatter_raw,
    yaml_util,
)
from frontmatter_format._libyaml_guard import needs_pure_parser
from frontmatter_format.yaml_util import (
    CHECKED_LIBYAML_VERSION,
    add_default_yaml_customizer,
    from_yaml_string,
    new_yaml,
    read_yaml_file,
    to_yaml_string,
    yaml_parser_mode,
)

C_PARSER: Any = getattr(ruamel.yaml.main, "CParser", None)  # noqa: B009
C_EMITTER: Any = getattr(ruamel.yaml.main, "CEmitter", None)  # noqa: B009

requires_c = pytest.mark.skipif(
    C_PARSER is None,
    reason="ruamel.yaml.clib (_ruamel_yaml) is not installed, so there is no C parser to compare",
)

REPO = Path(__file__).resolve().parents[1]
PURE_ENV = "FRONTMATTER_FORMAT_PURE_YAML"


# ---- Readings to compare ----------------------------------------------------------------


def canon(value: Any) -> Any:
    """A comparable form of a loaded value: types, key order, float bits and sharing."""
    ids: dict[int, int] = {}

    def go(v: Any) -> Any:
        if isinstance(v, (dict, list, tuple, set, frozenset)):
            key: int = id(cast(object, v))
            if key in ids:
                return ("ref", ids[key])
            ids[key] = len(ids)
            if isinstance(v, dict):
                items = cast(dict[Any, Any], v).items()
                return ("dict", tuple((go(k), go(x)) for k, x in items))
            members = cast(Iterable[Any], v)
            if isinstance(v, (set, frozenset)):
                return ("set", tuple(sorted(repr(go(x)) for x in members)))
            return (type(cast(object, v)).__name__, tuple(go(x) for x in members))
        if isinstance(v, float):
            return ("float", "nan" if math.isnan(v) else v.hex())
        if isinstance(v, (datetime, date)):
            return (type(v).__name__, repr(v), str(getattr(v, "tzinfo", None)))
        return (type(v).__name__, repr(v))

    return go(value)


def outcome(read: Callable[[str], Any], text: str) -> tuple[Any, ...]:
    """What `read` returns, in comparable form, or the type and message of what it raises."""
    try:
        return ("ok", canon(read(text)))
    except RecursionError:
        return ("error", "RecursionError")
    except Exception as e:
        return ("error", type(e).__name__, str(e))


def read_pure(text: str) -> Any:
    """Pure ruamel's reading through `new_yaml()`'s loader, set up independently of the
    library's own choice of parser."""
    yaml = new_yaml()
    yaml.Parser = Parser
    return yaml.load(text)


def read_raw_c(text: str) -> Any:
    """libyaml's reading through `new_yaml()`'s loader, with no guard or fallback."""
    yaml = new_yaml()
    yaml.Parser = C_PARSER
    return yaml.load(text)


@pytest.fixture
def pure_switch(monkeypatch: pytest.MonkeyPatch) -> Callable[[], None]:
    def turn_on() -> None:
        monkeypatch.setenv(PURE_ENV, "1")

    monkeypatch.delenv(PURE_ENV, raising=False)
    return turn_on


@pytest.fixture
def spies(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Record each C attempt and each pure reading the library makes."""
    calls: dict[str, list[str]] = {"c": [], "pure": []}
    load_with_c = yaml_util._load_with_c  # pyright: ignore[reportPrivateUsage]
    load_pure = yaml_util._load_pure  # pyright: ignore[reportPrivateUsage]

    def spy_c(yaml: YAML, text: str) -> Any:
        calls["c"].append(text)
        return load_with_c(yaml, text)

    def spy_pure(yaml: YAML, text: Any) -> Any:
        calls["pure"].append(text)
        return load_pure(yaml, text)

    monkeypatch.setattr(yaml_util, "_load_with_c", spy_c)
    monkeypatch.setattr(yaml_util, "_load_pure", spy_pure)
    monkeypatch.delenv(PURE_ENV, raising=False)
    return calls


# ---- The reported failure: libyaml rejects a colon inside a flow collection -------------

FLOW_COLON = {
    "sources: [https://example.com/a]\n": {"sources": ["https://example.com/a"]},
    "t: [10:30, 11:00]\n": {"t": ["10:30", "11:00"]},
    "m: {a: b:c}\n": {"m": {"a": "b:c"}},
}


@requires_c
@pytest.mark.parametrize("text", FLOW_COLON)
def test_flow_colon_document_reads_as_pure_ruamel_reads_it(text: str):
    with pytest.raises(Exception, match="found unexpected ':'"):
        read_raw_c(text)  # The fixture discriminates: libyaml alone refuses it.
    assert from_yaml_string(text) == FLOW_COLON[text]
    assert outcome(from_yaml_string, text) == outcome(read_pure, text)


@requires_c
def test_frontmatter_with_flow_colon_reads_from_files(tmp_path: Path):
    metadata = "process:\n  inputs: [https://example.com/a, b]\n  window: [10:30, 11:00]\n"
    expected = {"process": {"inputs": ["https://example.com/a", "b"], "window": ["10:30", "11:00"]}}
    doc = tmp_path / "spec.process.md"
    doc.write_text(f"---\n{metadata}---\nBody.\n", encoding="utf-8")
    plain = tmp_path / "spec.yml"
    plain.write_text(metadata, encoding="utf-8")

    assert fmf_read_frontmatter(doc) == expected
    assert fmf_read(doc) == ("Body.\n", expected)
    assert read_yaml_file(plain) == expected


# ---- Routing: shapes libyaml would read differently go straight to pure ruamel -----------

LIBYAML_DIFFERS = {
    # A line starting with `%`, where a directive can be.
    "yaml 1.1 directive": "%YAML 1.1\n---\nk: yes\nnum: 017\n",
    "yaml 1.1 directive after CR": "# c\r%YAML 1.1\r---\rk: yes\r",
    # Characters libyaml treats differently.
    "tab after a value": "a: b\t",
    "tab after flow mapping": '{"a": 1}\t',
    "NEL between entries": "-\x85-",
    "LS in a sequence": "a:\n  - b\n\u2028  -\n",
    "BOM at a line start": "a: \r\n\ufeffb: 2\n",
    # Block scalars.
    "block header comment without space": "a: |#c\n  x\n",
    "block space line before deeper line": "k: |\n \n  a\n",
    "root block scalar": "|\n#x\n",
    "root block scalar after a marker": "--- |\n#x\n",
    # Flow and key indicators.
    "quoted key in flow sequence": '["a":1]',
    "question colon in flow": "k: [?:]\n",
    "empty explicit key in flow": "k: [? ]]\n",
    "explicit key then colon in flow": "[? :]",
    "explicit key, anchor, colon in flow": "[?&a :]",
    "explicit flow key in flow": "[?[a] :]",
    "anchor before a colon in flow": "[&a :]",
    "tag before a colon in flow": "[!!str :]",
    "flow sequence key then colon": "[[]:]",
    "flow sequence key then colon in a value": "k: [[a]:b]\n",
    "flow sequence key then colon after an entry": "[a, []:x]",
    "tagged flow sequence key then colon": "[!!seq []:x]",
    "anchored flow sequence key then colon": "[&y []:x]",
    "flow sequence key then colon after a marker": "--- [[a, b]:1]",
    # Anchors, tags and markers.
    "root block scalar with a tag on the marker line": "--- !!str\n|\n#x\n",
    "root block scalar with a tag and a comment": "--- !!str # c\n|\n#x\n",
    "root block scalar with an indented header after a tag": "--- !!str\n  |\n#x\n",
    "root block scalar with an anchor on its own line": "&a\n|\n#x\n",
    "root block scalar with a tag then an anchor line": "!!str\n&a\n|\n#x\n",
    "root block scalar with a tag, CRLF": "--- !!str\r\n|\r\n#x\r\n",
    "root binary block scalar with a tag line": "!!binary\n|\n#x\n",
    "verbatim empty tag on an empty value": "k: !<!>\n",
    "verbatim empty tag on an empty entry": "- !<!>\n",
    "verbatim empty tag as the document": "!<!>",
    "verbatim empty tag as a flow key": "{!<!> : 1}",
    "verbatim empty tag after an anchor": "k: &a !<!>\n",
    "anchor name with colon": "&a: 1\n",
    "anchor on a key after a key": "a: 1\n&b: 2\n",
    "empty non-specific tag": "k: !\n",
    "empty non-specific tag after CR": "\r!",
    "second document end marker": "a: 1\n...\n...\n",
    "second document end marker after CR": "a: 1\r...\r...\r",
}
"""Texts libyaml reads without raising, but not as pure ruamel does: it either returns a
different value or accepts a text pure ruamel refuses. No fallback can catch these."""

ROUTED_BY_RULE = {
    "unknown directive": "%FOO bar\n---\nk: v\n",
    "tag directive": "%TAG !e! tag:yaml.org,2002:\n---\nk: !e!str 1\n",
    "NEL in a plain scalar": "k: a\x85b\n",
    "BOM at a line start, rejected": "a: 1\n\ufeffb: 2\n",
}
"""Texts libyaml rejects or reads correctly that the same rules route anyway."""

ROUTED = {**LIBYAML_DIFFERS, **ROUTED_BY_RULE}


@requires_c
@pytest.mark.parametrize("name", LIBYAML_DIFFERS)
def test_each_guard_covers_a_text_libyaml_reads_differently_without_raising(name: str):
    """Pins each guard to a real difference that a fallback could not see."""
    text = LIBYAML_DIFFERS[name]
    raw = outcome(read_raw_c, text)
    assert raw[0] == "ok"
    assert raw != outcome(read_pure, text)


@requires_c
@pytest.mark.parametrize("name", ROUTED)
def test_routed_shapes_never_reach_libyaml(name: str, spies: dict[str, list[str]]):
    text = ROUTED[name]
    result = outcome(from_yaml_string, text)
    assert spies["c"] == []
    assert spies["pure"] == [text]
    assert result == outcome(read_pure, text)


@requires_c
@pytest.mark.parametrize("name", LIBYAML_DIFFERS)
def test_texts_libyaml_reads_differently_come_out_as_pure_ruamel_says(name: str):
    text = LIBYAML_DIFFERS[name]
    assert outcome(from_yaml_string, text) == outcome(read_pure, text)


@requires_c
def test_directives_change_values_as_pure_ruamel_says():
    assert from_yaml_string(LIBYAML_DIFFERS["yaml 1.1 directive"]) == {"k": True, "num": 15}
    assert from_yaml_string(ROUTED_BY_RULE["unknown directive"]) == {"k": "v"}
    assert from_yaml_string(ROUTED_BY_RULE["tag directive"]) == {"k": "1"}


ORDINARY = [
    "title: A Title\nauthor: Jane Doe\ntags: [a, b]\n",
    "k: v\nn: 3\nf: 1.5\nd: 2024-01-02\nnested:\n  - x: 1\n    y: [1, 2]\n",
    "description: |\n  Two lines\n  of text.\nflow: {a: 1, b: [x, y]}\n",
]


@requires_c
@pytest.mark.parametrize("text", ORDINARY)
def test_ordinary_documents_are_read_once_by_libyaml(text: str, spies: dict[str, list[str]]):
    result = from_yaml_string(text)
    assert spies == {"c": [text], "pure": []}
    assert canon(result) == canon(read_pure(text))


# ---- Fallback: any failure of the C attempt is answered by pure ruamel -------------------

NATURAL_C_FAILURES = {
    "flow colon (libyaml ScannerError)": "sources: [https://example.com/a]\n",
    "time in a flow sequence (libyaml ScannerError)": "t: [10:30, 11:00]\n",
    "raw surrogate (UnicodeEncodeError)": "k: \ud800\n",
    "escaped surrogate (libyaml refuses, pure reads)": 'k: "\\ud800"\n',
    "unclosed flow sequence (message differs)": "k: [a\n",
    "duplicate key (message differs)": "a: 1\na: 2\n",
}


@requires_c
@pytest.mark.parametrize("name", NATURAL_C_FAILURES)
def test_a_c_failure_is_answered_exactly_by_pure_ruamel(name: str, spies: dict[str, list[str]]):
    text = NATURAL_C_FAILURES[name]
    raw, pure = outcome(read_raw_c, text), outcome(read_pure, text)
    assert raw[0] == "error" and raw != pure  # The fixture discriminates.
    assert outcome(from_yaml_string, text) == pure
    assert spies == {"c": [text], "pure": [text]}


def _never(_text: str) -> bool:
    return False


@requires_c
@pytest.mark.parametrize("name", ["NEL in a plain scalar", "unknown directive"])
def test_with_routing_off_libyaml_rejections_still_come_out_as_pure(
    name: str, spies: dict[str, list[str]], monkeypatch: pytest.MonkeyPatch
):
    """The fallback alone already covers the shapes libyaml rejects."""
    monkeypatch.setattr(yaml_util, "needs_pure_parser", _never)
    text = ROUTED[name]
    assert outcome(read_raw_c, text)[0] == "error"
    assert outcome(from_yaml_string, text) == outcome(read_pure, text)
    assert spies == {"c": [text], "pure": [text]}


class _FakeCParser:
    """Stands in for ruamel's C parser and raises when ruamel builds it during a load."""

    raised: BaseException = ValueError("injected")
    built: int = 0

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        type(self).built += 1
        raise type(self).raised


@pytest.fixture
def fake_c(monkeypatch: pytest.MonkeyPatch) -> type[_FakeCParser]:
    """Simulate an installed extension whose parser raises a chosen exception."""
    fake = type("FakeCParser", (_FakeCParser,), {"built": 0})
    monkeypatch.setattr(yaml_util, "_CParser", fake)
    monkeypatch.setattr(yaml_util, "_C_PARSER_CHECKED", True)
    monkeypatch.delenv(PURE_ENV, raising=False)
    return fake


@pytest.mark.parametrize(
    "raised",
    [
        ValueError("injected"),
        RecursionError("injected"),
        MemoryError("injected"),
        RuntimeError("injected"),
        KeyError("injected"),
        UnicodeEncodeError("utf-8", "x", 0, 1, "injected"),
        ruamel.yaml.error.YAMLError("injected"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_any_exception_in_the_c_attempt_falls_back(raised: Exception, fake_c: type[_FakeCParser]):
    fake_c.raised = raised
    text = ORDINARY[0]
    assert from_yaml_string(text) == read_pure(text)
    assert fake_c.built == 1


def test_keyboard_interrupt_in_the_c_attempt_is_not_swallowed(fake_c: type[_FakeCParser]):
    fake_c.raised = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        from_yaml_string(ORDINARY[0])


def _nested(depth: int) -> str:
    return "k: " + "[" * depth + "]" * depth + "\n"


@requires_c
def test_values_nested_past_the_c_limit_are_read_again_by_pure(spies: dict[str, list[str]]):
    text = _nested(yaml_util._C_MAX_DEPTH + 20)  # pyright: ignore[reportPrivateUsage]
    assert outcome(read_raw_c, text)[0] == "ok"
    assert outcome(from_yaml_string, text) == outcome(read_pure, text)
    assert spies == {"c": [text], "pure": [text]}


@requires_c
def test_nesting_pure_ruamel_cannot_compose_raises_as_pure_ruamel_does():
    text = _nested(600)
    assert isinstance(read_raw_c(text), dict)  # libyaml alone reads it.
    with pytest.raises(RecursionError):
        read_pure(text)
    with pytest.raises(RecursionError):
        from_yaml_string(text)


@requires_c
def test_aliased_collections_keep_pure_ruamels_sharing(spies: dict[str, list[str]]):
    text = "a: &x [1, {b: 2}]\nc: *x\nm:\n  <<: &base {p: 1}\n  q: 2\nbase: *base\n"
    result = from_yaml_string(text)
    assert result["a"] is result["c"]
    assert canon(result) == canon(read_pure(text))
    assert spies == {"c": [], "pure": [text]}  # Anchors and aliases are routed to pure.
    # The node walk still discards a shared node, should an alias ever reach libyaml.
    yaml = new_yaml()
    assert yaml_util._load_with_c(yaml, text) is yaml_util._C_FAILED  # pyright: ignore[reportPrivateUsage]


def test_a_customizer_that_changes_loading_keeps_the_pure_parser(
    fake_c: type[_FakeCParser], monkeypatch: pytest.MonkeyPatch
):
    """ruamel's C loader would bypass a replaced composer, so the C parser is not used."""
    from ruamel.yaml.composer import Composer

    composed: list[str] = []

    class RecordingComposer(Composer):
        def compose_document(self) -> Any:  # pyright: ignore[reportImplicitOverride]
            composed.append("x")
            return super().compose_document()

    def customize(yaml: YAML) -> None:
        yaml.Composer = RecordingComposer

    monkeypatch.setattr(yaml_util, "_default_yaml_customizers", [])
    add_default_yaml_customizer(customize)
    assert from_yaml_string("k: v\n") == {"k": "v"}
    assert fake_c.built == 0
    assert composed == ["x"]
    assert yaml_parser_mode() == "pure"  # The report follows the reader, not the install.


# ---- The switch and the report -----------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "mode"),
    [(None, "c-first"), ("", "c-first"), ("0", "c-first"), ("1", "pure"), ("yes", "pure")],
)
def test_switch_values(value: str | None, mode: str, monkeypatch: pytest.MonkeyPatch):
    from frontmatter_format import PURE_YAML_ENV, yaml_parser_mode

    assert PURE_YAML_ENV == PURE_ENV
    monkeypatch.setattr(yaml_util, "_CParser", _FakeCParser)
    monkeypatch.setattr(yaml_util, "_C_PARSER_CHECKED", True)
    if value is None:
        monkeypatch.delenv(PURE_ENV, raising=False)
    else:
        monkeypatch.setenv(PURE_ENV, value)
    assert yaml_parser_mode() == mode


def test_report_is_pure_without_the_extension(monkeypatch: pytest.MonkeyPatch):
    from frontmatter_format import yaml_parser_mode

    monkeypatch.setattr(yaml_util, "_CParser", None)
    monkeypatch.delenv(PURE_ENV, raising=False)
    assert yaml_parser_mode() == "pure"


def test_report_in_a_process_that_cannot_import_the_extension():
    code = (
        "import sys; sys.modules['_ruamel_yaml'] = None\n"
        "import frontmatter_format as f; print(f.yaml_parser_mode())\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "pure"


@requires_c
def test_report_is_c_first_with_the_extension(monkeypatch: pytest.MonkeyPatch):
    from frontmatter_format import yaml_parser_mode

    monkeypatch.delenv(PURE_ENV, raising=False)
    assert yaml_parser_mode() == "c-first"


@requires_c
def test_the_pure_switch_keeps_libyaml_out(
    spies: dict[str, list[str]], pure_switch: Callable[[], None]
):
    pure_switch()
    assert from_yaml_string(ORDINARY[0]) == read_pure(ORDINARY[0])
    assert spies == {"c": [], "pure": [ORDINARY[0]]}


# ---- Dumping and the factory -------------------------------------------------------------


@pytest.mark.parametrize("typ", ["safe", "base", "full"])
def test_new_yaml_hands_out_the_pure_parser_and_emitter(typ: Any):
    yaml = new_yaml(typ=typ)
    assert yaml.Parser is Parser
    assert yaml.Emitter is Emitter


def test_round_trip_handles_are_unchanged():
    yaml = new_yaml(typ="rt")
    assert yaml.Parser is RoundTripParser
    assert yaml.Emitter is RoundTripEmitter


SAFE_DUMP_VALUE = {"emoji": "😀", "astral": "\U0001d11e", "long": "word " * 40}


def _safe_dump_without_extension() -> str:
    code = (
        "import sys, json; sys.modules['_ruamel_yaml'] = None\n"
        "from frontmatter_format import to_yaml_string\n"
        "print(json.dumps(to_yaml_string(json.loads(sys.argv[1]), typ='safe')))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code, json.dumps(SAFE_DUMP_VALUE)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


@requires_c
def test_safe_dumps_write_the_bytes_of_a_process_without_the_extension():
    expected = _safe_dump_without_extension()
    assert to_yaml_string(SAFE_DUMP_VALUE, typ="safe") == expected
    assert "emoji: 😀\n" in expected

    unpinned = YAML(typ="safe")  # The fixture discriminates: libyaml's emitter differs.
    assert unpinned.Emitter is C_EMITTER
    stream = StringIO()
    unpinned.dump(SAFE_DUMP_VALUE, stream)
    assert stream.getvalue() != expected


# ---- The guards are linear ---------------------------------------------------------------

GUARD_GROWTH_FAMILIES: dict[str, tuple[str, str, str]] = {
    # name: (prefix, unit repeated n times, suffix). Each unit once hung or dragged a guard.
    "hash banner": ("", "#", "\nkey: value\n"),
    "issue references in a comment": ("# see ", "#1, ", "\nk: v\n"),
    "comment lines with trailing spaces": ("", "# c  \n", "k: v\n"),
    "pipe-hash cells on one line": ("k: |\n  ", "| #n cell ", "\n"),
    "space-only lines in a block scalar": ("k: |\n", "  x\n  \n", ""),
    "consecutive space-only lines": ("k: |\n  x\n", "  \n", ""),
    "space-only lines in a CR block scalar": ("k: |\r", "  x\r  \r", ""),
    "colons after spaces": ("k: ", "a : ", "\n"),
    "quoted scalars and colons in flow": ("k: [", "'a', b:c, ", "]\n"),
    "anchors and tags": ("", "- &a !t x\n", ""),
    "anchor lines with comments": ("", "&a # c\n", "x\n"),
    "tag lines": ("", "!!str\n", "x\n"),
    "verbatim tags": ("k: [", "!<!> a, ", "]\n"),
    "flow openers": ("k: ", "[a, {b: c}], ", "\n"),
    "indicator chains": ("", "- ", "x\n"),
}
"""Adversarial shapes: a long `#` banner and `# see #1, #2` once took seconds to minutes in
`_ROOT_BLOCK_SCALAR`, and `| #` cells and space-only lines made the space-line rule
quadratic (consecutive space-only lines did so again in a first rewrite, whose backward
search was bounded at the previous match's end). The rest cover every other guard and the
nesting bound."""

_TIMING_CODE = """
import json, sys, time
from frontmatter_format._libyaml_guard import needs_pure_parser
from frontmatter_format.yaml_util import _nesting_bound
families, sizes = json.loads(sys.argv[1]), json.loads(sys.argv[2])
def best(fn, text):
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        fn(text)
        times.append(time.perf_counter() - t0)
    return min(times)
out = {}
for name, (prefix, unit, suffix) in families.items():
    out[name] = [
        [best(needs_pure_parser, prefix + unit * n + suffix), best(_nesting_bound, prefix + unit * n + suffix)]
        for n in sizes
    ]
print(json.dumps(out))
"""


def _guard_times(sizes: list[int]) -> dict[str, list[list[float]]]:
    """Best-of-5 seconds of the guard and the nesting bound on each family at each size, in a
    subprocess with a deadline, so a guard that hangs again fails instead of hanging the
    suite."""
    out = subprocess.run(
        [sys.executable, "-c", _TIMING_CODE, json.dumps(GUARD_GROWTH_FAMILIES), json.dumps(sizes)],
        capture_output=True,
        text=True,
        timeout=300,
        check=True,
    )
    return json.loads(out.stdout)


def test_guards_finish_on_large_adversarial_texts():
    """A hang guard, not a timing gate: every family at 100,000 units must finish inside the
    subprocess deadline in `_guard_times`. The unfixed `_ROOT_BLOCK_SCALAR` needed over 60 s
    for a 40-`#` banner and the quadratic space-line rule minutes at this size, so the
    deadline discriminates without a threshold a shared runner could trip."""
    times = _guard_times([100_000])
    assert set(times) == set(GUARD_GROWTH_FAMILIES)


@pytest.mark.slow
def test_guards_grow_linearly_with_the_text():
    """A hundred times the text must cost under a thousand times the time: linear is about
    100x (less, with the fixed cost per call), quadratic about 10,000x. Best of five runs on
    each side keeps timer noise out, and the ratio is within one run, so a slow or shared
    machine moves both sides alike. Still a wall-clock measurement (review D of PR #9 saw
    ratios up to 449 under heavy contention), so it is in the `slow` tier, outside the
    default run; `test_the_space_line_guard_looks_back_only_as_far_as_the_previous_line` is
    the deterministic gate for the one guard with Python-level looping."""
    small_size, big_size = 1_000, 100_000
    times = _guard_times([small_size, big_size])
    ratios = {
        name: (round(big / max(small, 1e-5)), round(big_bound / max(small_bound, 1e-5)))
        for name, [[small, small_bound], [big, big_bound]] in times.items()
    }
    limit = (big_size // small_size) * 10
    superlinear = {name: r for name, r in ratios.items() if r[0] >= limit or r[1] >= limit}
    assert superlinear == {}, ratios


class _CountingText(str):
    """A `str` that records how many characters its `rfind` calls may scan."""

    __slots__: tuple[str, ...] = ("calls", "scanned")
    calls: int
    scanned: int

    def __new__(cls, text: str) -> _CountingText:
        self = super().__new__(cls, text)
        self.calls = 0
        self.scanned = 0
        return self

    def rfind(self, sub: str, start: int = 0, end: int | None = None, /) -> int:  # pyright: ignore[reportIncompatibleMethodOverride, reportImplicitOverride]
        self.calls += 1
        self.scanned += (len(self) if end is None else end) - start
        return super().rfind(sub, start, end)


class _CountingSearch:
    """Stands in for `_BLOCK_HEADER_AT_LINE_END` and records the span of each search."""

    pattern: re.Pattern[str]
    scanned: int

    def __init__(self, pattern: re.Pattern[str]) -> None:
        self.pattern = pattern
        self.scanned = 0

    def search(self, text: str, pos: int, endpos: int) -> re.Match[str] | None:
        self.scanned += endpos - pos
        return self.pattern.search(text, pos, endpos)


SPACE_LINE_SHAPES: dict[str, Callable[[int], str]] = {
    "space-only lines in a block scalar": lambda n: "k: |\n" + "  x\n  \n" * n,
    "consecutive space-only lines": lambda n: "k: |\n  x\n" + "  \n" * n,
    "space-only lines with CR endings": lambda n: "k: |\r" + "  x\r  \r" * n,
    "space-only lines after values": lambda n: "a: 1\n" + " \n" * n,
    "a header before the space lines": lambda n: "k: | #c\n" + "  \n" * n,
}


@pytest.mark.parametrize("n", [1, 2_000, 20_000])
@pytest.mark.parametrize("shape", SPACE_LINE_SHAPES.values(), ids=SPACE_LINE_SHAPES.keys())
def test_the_space_line_guard_looks_back_only_as_far_as_the_previous_line(
    shape: Callable[[int], str], n: int, monkeypatch: pytest.MonkeyPatch
):
    """The loop hands `rfind` at most twice the text and the header search at most once.

    A deterministic proxy for the loop's cost, counted rather than timed, so it cannot flake
    on a shared runner. Each space-only line costs two `rfind` calls bounded by the previous
    match and one search over the line before it; the spans telescope, so the totals are at
    most twice and once the text, whatever `n` is. Searching from 0 hands `rfind` about `n`
    times the text, and bounding by the previous match's end hands the header search the
    whole prefix on consecutive space-only lines; both fail here by orders of magnitude.
    """
    plain = shape(n)
    expected = _libyaml_guard._block_scalar_before_space_line(plain)  # pyright: ignore[reportPrivateUsage]
    text = _CountingText(plain)
    search = _CountingSearch(_libyaml_guard._BLOCK_HEADER_AT_LINE_END)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_libyaml_guard, "_BLOCK_HEADER_AT_LINE_END", search)

    assert _libyaml_guard._block_scalar_before_space_line(text) is expected  # pyright: ignore[reportPrivateUsage]

    space_only_lines = sum(1 for _ in _libyaml_guard._SPACE_ONLY_LINE.finditer(plain))  # pyright: ignore[reportPrivateUsage]
    assert space_only_lines >= n
    if expected:
        assert text.calls <= 2 * space_only_lines  # A hit ends the loop at that line.
    else:
        assert text.calls == 2 * space_only_lines
    assert text.scanned <= 2 * len(text), (text.calls, text.scanned, len(text))
    assert search.scanned <= len(text), (search.scanned, len(text))


def test_a_space_only_line_routes_only_after_a_block_scalar_header():
    check = _libyaml_guard._block_scalar_before_space_line  # pyright: ignore[reportPrivateUsage]
    assert check("k: |\n \n  a\n")
    assert check("k: >-  \n \n  a\n")
    assert check("k: | # c\n \n  a\n")
    assert check("k: |\r \r  a\r")
    assert check("a: 1\r\nk: |\r\n \r\n  a\r\n")
    assert not check("k: |\n  x\n  \n  y\n")  # The line before the space line is content.
    assert not check("k: | #c\n  x\n  \n  \n")  # A header two lines up is not the line before.
    assert not check("k: v  \n \n")  # No header.
    assert not check("k: |\n ")  # The space line is not terminated.


@requires_c
def test_a_pipe_inside_a_leading_comment_no_longer_routes(spies: dict[str, list[str]]):
    text = "# usage: a | b > c\nk: v\n"
    assert from_yaml_string(text) == {"k": "v"}
    assert spies == {"c": [text], "pure": []}


@pytest.mark.parametrize(
    "text",
    [
        "&a x",
        "k: !!str x",
        "- *a",
        "[!<!> x]",
        "{a: &b 1}",
        "k:\n  !t x",
        "? &k\n: v",
        "-&a",
        "?!x",
    ],
)
def test_a_property_or_alias_at_a_token_start_routes(text: str):
    assert needs_pure_parser(text)


@pytest.mark.parametrize(
    "text",
    ["t: Tom&Jerry", "t: Hello!", "n: a*b", "u: http://x/?a=1&b=2", "t: 'Tom & Jerry'", "k: a!"],
)
def test_a_property_character_inside_content_does_not_route(text: str):
    """Only a token start can begin a property; elsewhere `!`, `&` and `*` are content to both
    parsers. (`'Tom & Jerry'`: the `&` follows a space inside the quotes, so it routes; the
    quote-opened scalar is content, and the cost is only speed. Listed as a reminder.)"""
    if text == "t: 'Tom & Jerry'":
        assert needs_pure_parser(text)
    else:
        assert not needs_pure_parser(text)


# ---- Deep nesting never reaches the C composer -----------------------------------------


def _deep_text(shape: str, depth: int) -> str:
    if shape == "flow":
        return "k: " + "[" * depth + "]" * depth + "\n"
    if shape == "flowmap":
        return "k: " + "{a: " * depth + "1" + "}" * depth + "\n"
    if shape == "dash":
        return "- " * depth + "x\n"
    assert shape == "question"
    return "? " * depth + "x\n"


def test_nesting_bound_is_an_upper_bound_and_small_on_ordinary_documents():
    bound = yaml_util._nesting_bound  # pyright: ignore[reportPrivateUsage]
    assert bound(_deep_text("flow", 50)) >= 50
    assert bound(_deep_text("flowmap", 50)) >= 50
    assert bound(_deep_text("dash", 50)) >= 50
    assert bound(_deep_text("question", 50)) >= 50
    assert bound("- - - - a: [b, {c: d}]\n  - - x\n") >= 8
    assert bound("".join(" " * i + "- \n" for i in range(30)) + " " * 30 + "x\n") >= 30
    assert bound("a:\n- b:\n  - c:\n    - d: 1\n") >= 7
    assert bound("k: a[b[c[d # x[\nurl: http://x/[1]\n") == 2  # Brackets inside words are content.
    assert all(bound(text) < 20 for text in ORDINARY)
    limit = yaml_util._C_SCAN_DEPTH  # pyright: ignore[reportPrivateUsage]
    assert bound("k: [a]\n" * (limit // 2)) <= limit  # Wide, not deep: stays on libyaml.


@requires_c
@pytest.mark.parametrize("shape", ["flow", "flowmap", "dash", "question"])
def test_texts_that_may_nest_past_the_scan_bound_skip_the_c_parser(
    shape: str, spies: dict[str, list[str]]
):
    text = _deep_text(shape, max(yaml_util._C_SCAN_DEPTH + 200, 600))  # pyright: ignore[reportPrivateUsage]
    assert (
        outcome(from_yaml_string, text) == outcome(read_pure, text) == ("error", "RecursionError")
    )
    assert spies == {"c": [], "pure": [text]}


@requires_c
@pytest.mark.parametrize(
    ("shape", "depth"),
    [
        ("flow", 30_000),
        ("flowmap", 30_000),
        ("dash", 40_000),
        ("question", 40_000),
        ("flow", 100_000),
    ],
)
def test_nesting_past_the_c_stack_raises_as_pure_ruamel_does_instead_of_crashing(
    shape: str, depth: int
):
    """ruamel's C composer segfaults at about 30,000 levels on an 8 MB stack (measured here
    for the raw C parser on these shapes); the readers must answer with pure ruamel's
    `RecursionError`. Run in a subprocess so that a crash is a failure, not a lost run."""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(Path(__file__).parent)!r})\n"
        "from test_c_parser import _deep_text\n"
        "from frontmatter_format import from_yaml_string, yaml_parser_mode\n"
        "assert yaml_parser_mode() == 'c-first'\n"
        "try:\n"
        f"    from_yaml_string(_deep_text({shape!r}, {depth}))\n"
        "    print('ok')\n"
        "except RecursionError:\n"
        "    print('RecursionError')\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env={k: v for k, v in os.environ.items() if k != PURE_ENV},
    )
    assert out.returncode == 0, out.stderr[-500:]
    assert out.stdout.strip() == "RecursionError"


_THREAD_CODE = """
import os, sys, threading
depth, stack_kb, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
if mode == "pure":
    os.environ["FRONTMATTER_FORMAT_PURE_YAML"] = "1"
import ruamel.yaml.main
from frontmatter_format import from_yaml_string, yaml_parser_mode
from frontmatter_format.yaml_util import new_yaml
assert yaml_parser_mode() == ("pure" if mode == "pure" else "c-first")
text = "k: " + "[" * depth + "]" * depth + "\\n"
result = []
def run():
    try:
        if mode == "raw":
            yaml = new_yaml()
            yaml.Parser = ruamel.yaml.main.CParser
            value = yaml.load(text)
        else:
            value = from_yaml_string(text)
        result.append("ok " + str(len(repr(value))))
    except RecursionError:
        result.append("RecursionError")
threading.stack_size(stack_kb * 1024)
thread = threading.Thread(target=run)
thread.start()
thread.join()
print(result[0])
"""


def _read_on_a_thread(depth: int, stack_kb: int, mode: str) -> tuple[int, str]:
    """`from_yaml_string` (or the raw C parser) on a `depth`-deep flow document, on a thread
    with a `stack_kb` stack, in a subprocess: its exit code and printed outcome. A segfault
    is a negative exit code, never a lost suite."""
    out = subprocess.run(
        [sys.executable, "-c", _THREAD_CODE, str(depth), str(stack_kb), mode],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env={k: v for k, v in os.environ.items() if k != PURE_ENV},
    )
    return out.returncode, out.stdout.strip() or out.stderr[-300:]


@requires_c
def test_the_c_composer_survives_the_scan_bound_on_a_small_thread_stack():
    """Review E of PR #9: the C composer overflows a 128 KB thread stack (musl's default) at
    about 400 levels and segfaults on CPython 3.10 to 3.13, so a text the bound lets through
    must stay well under that. Raw libyaml composes `_C_SCAN_DEPTH` levels on such a thread;
    the reader then gives pure ruamel's answer for a document just under the bound, and the
    same again on an 8 MB stack. Fails before the bound was lowered from 1,000."""
    limit = yaml_util._C_SCAN_DEPTH  # pyright: ignore[reportPrivateUsage]
    assert _read_on_a_thread(limit, 128, "raw")[0] == 0
    big_stack = _read_on_a_thread(limit - 10, 8192, "pure")
    assert big_stack[0] == 0 and big_stack[1].startswith("ok")
    assert _read_on_a_thread(limit - 10, 8192, "c-first") == big_stack
    small_stack = _read_on_a_thread(limit - 10, 128, "pure")
    if small_stack[0] != 0:
        # Python 3.10 spends C stack on every Python frame, and pure ruamel's own recursion
        # overflows 128 KB before the bound; the raw check above is what matters there.
        pytest.skip(f"pure ruamel itself overflows a 128 KB stack here: exit {small_stack[0]}")
    assert _read_on_a_thread(limit - 10, 128, "c-first") == small_stack == big_stack


@requires_c
def test_a_document_past_the_scan_bound_on_a_small_thread_stack_raises_as_pure_does():
    """600 levels on a 128 KB thread: the C composer would segfault on CPython 3.10 to 3.13
    (and did, when the bound was 1,000); the reader must answer with pure ruamel's
    `RecursionError`. On Python 3.10 pure ruamel itself overflows this stack, so the case
    is skipped there."""
    pure = _read_on_a_thread(600, 128, "pure")
    if pure[0] != 0:
        pytest.skip(f"pure ruamel itself overflows a 128 KB stack here: exit {pure[0]}")
    assert pure[1] == "RecursionError"
    assert _read_on_a_thread(600, 128, "c-first") == pure


# ---- One instance per read, left clean by the C attempt --------------------------------


@requires_c
@pytest.mark.parametrize(
    "text",
    [
        ORDINARY[0],
        NATURAL_C_FAILURES["flow colon (libyaml ScannerError)"],
        LIBYAML_DIFFERS["tab after a value"],
        _nested(120),
    ],
    ids=["libyaml reads it", "libyaml fails", "routed", "deep value discarded"],
)
def test_default_customizers_run_once_per_read(text: str, monkeypatch: pytest.MonkeyPatch):
    calls: list[int] = []
    counting: list[Callable[[YAML], None]] = [lambda _yaml: calls.append(1)]
    monkeypatch.setattr(yaml_util, "_default_yaml_customizers", counting)
    outcome(from_yaml_string, text)
    assert calls == [1]


@requires_c
def test_a_stateful_customizer_sees_one_instance_per_read(monkeypatch: pytest.MonkeyPatch):
    """Qodo's case: a customizer that toggles `allow_duplicate_keys` on each call. The pure
    re-read uses the instance the C attempt used, so one pure load and the reader agree."""
    state = {"calls": 0}

    def toggling(yaml: YAML) -> None:
        state["calls"] += 1
        yaml.allow_duplicate_keys = state["calls"] % 2 == 0

    monkeypatch.setattr(yaml_util, "_default_yaml_customizers", [toggling])
    text = "a: [http://x]\na: 2\n"  # libyaml fails on the flow colon; pure re-reads.
    with pytest.raises(DuplicateKeyError):
        from_yaml_string(text)
    assert state["calls"] == 1


@requires_c
def test_a_failed_c_attempt_leaves_the_instance_as_it_was():
    yaml = new_yaml()
    before = dict(vars(yaml))
    text = NATURAL_C_FAILURES["flow colon (libyaml ScannerError)"]
    failed = yaml_util._load_with_c(yaml, text)  # pyright: ignore[reportPrivateUsage]
    assert failed is yaml_util._C_FAILED  # pyright: ignore[reportPrivateUsage]
    assert set(vars(yaml)) == set(before) and yaml.Parser is Parser
    assert yaml.Constructor is before["Constructor"]
    assert yaml.load(text) == read_pure(text) == {"sources": ["https://example.com/a"]}


@requires_c
def test_a_kept_c_reading_leaves_the_instance_reusable():
    yaml = new_yaml()
    assert yaml_util._load_with_c(yaml, ORDINARY[0]) == read_pure(ORDINARY[0])  # pyright: ignore[reportPrivateUsage]
    assert yaml.Parser is Parser
    assert yaml.load(ORDINARY[1]) == read_pure(ORDINARY[1])


def test_an_instance_set_to_warn_on_duplicate_keys_keeps_the_pure_parser():
    """Review E of PR #9 (E5): a `DuplicateKeyFutureWarning` from a kept C reading carries
    libyaml's marks, without pure ruamel's source snippet, so the warn setting stays pure."""
    yaml = new_yaml()
    assert yaml_util._accepts_c_parser(yaml)  # pyright: ignore[reportPrivateUsage]
    yaml.allow_duplicate_keys = cast(Any, None)  # ruamel's "warn" setting.
    assert not yaml_util._accepts_c_parser(yaml)  # pyright: ignore[reportPrivateUsage]
    yaml.allow_duplicate_keys = True
    assert yaml_util._accepts_c_parser(yaml)  # pyright: ignore[reportPrivateUsage]


def test_accepts_the_c_parser_on_a_handle_without_max_depth():
    """ruamel.yaml 0.18 has no `YAML.max_depth`; the check must read it with a default."""
    yaml = new_yaml()
    if hasattr(yaml, "max_depth"):
        delattr(yaml, "max_depth")
    assert yaml_util._accepts_c_parser(yaml)  # pyright: ignore[reportPrivateUsage]
    yaml.max_depth = 5
    assert not yaml_util._accepts_c_parser(yaml)  # pyright: ignore[reportPrivateUsage]


@requires_c
def test_shared_empty_tuples_are_not_taken_for_aliases(spies: dict[str, list[str]]):
    text = "- {[]: a}\n- {[]: b}\n"  # Both keys are CPython's one empty tuple.
    assert outcome(from_yaml_string, text) == outcome(read_pure, text)
    assert spies == {"c": [text], "pure": []}


class _Box:
    items: Any

    def __init__(self, items: Any) -> None:
        self.items = items


def _construct_box(_constructor: Any, node: Any) -> _Box:
    return _Box(node.value)


def _register_box(yaml: YAML) -> None:
    yaml.Constructor.add_constructor("!box", _construct_box)


def _boxed(depth: int) -> str:
    return "k: " + "!box [" * depth + "]" * depth + "\n"


@requires_c
def test_a_tag_constructor_cannot_hide_depth_from_the_c_check(monkeypatch: pytest.MonkeyPatch):
    """Qodo 4370103219: a constructor that returns an object that is not a container for
    every `!box` sequence. Every tag is routed to pure ruamel now, so the reader never
    shows libyaml such a text; should one ever reach the C attempt, the depth check runs on
    the nodes libyaml composed, so the constructed value cannot hide the nesting."""
    monkeypatch.setattr(yaml_util, "_default_yaml_customizers", [_register_box])
    yaml = new_yaml()
    assert yaml_util._accepts_c_parser(yaml)  # pyright: ignore[reportPrivateUsage]
    deep = _boxed(600)
    assert needs_pure_parser(deep)  # The tag routes it.
    assert (
        outcome(from_yaml_string, deep) == outcome(read_pure, deep) == ("error", "RecursionError")
    )
    assert isinstance(read_raw_c(deep)["k"], _Box)  # libyaml alone reads it.
    assert yaml_util._load_with_c(yaml, deep) is yaml_util._C_FAILED  # pyright: ignore[reportPrivateUsage]
    shallow = _boxed(yaml_util._C_MAX_DEPTH - 1)  # pyright: ignore[reportPrivateUsage]
    assert isinstance(yaml_util._load_with_c(yaml, shallow)["k"], _Box)  # pyright: ignore[reportPrivateUsage]


@requires_c
def test_the_depth_check_runs_before_construction():
    constructed: list[str] = []

    def construct_noting(_constructor: Any, node: Any) -> str:
        constructed.append(node.tag)
        return "noted"

    yaml = new_yaml()
    yaml.Constructor.add_constructor("!note", construct_noting)
    deep = "k: !note " + "[" * 200 + "]" * 200 + "\n"
    assert yaml_util._load_with_c(yaml, deep) is yaml_util._C_FAILED  # pyright: ignore[reportPrivateUsage]
    assert constructed == []
    assert yaml_util._load_with_c(yaml, "k: !note [a]\n") == {"k": "noted"}  # pyright: ignore[reportPrivateUsage]
    assert constructed == ["!note"]


def test_node_walk_counts_depth_and_shared_nodes():
    walk = yaml_util._node_nested_deeper_than  # pyright: ignore[reportPrivateUsage]
    yaml = new_yaml()
    yaml.Parser = Parser

    def compose(text: str) -> Any:
        return yaml.compose(text)

    assert not walk(compose("a: 1\n"), 1)
    assert walk(compose("a: [1]\n"), 1) and not walk(compose("a: [1]\n"), 2)
    assert walk(compose("- [[[x]]]\n"), 3) and not walk(compose("- [[[x]]]\n"), 4)
    assert walk(compose("{[a]: 1}\n"), 1)  # Keys count too.
    assert walk(compose("a: &x [1]\nb: *x\n"), 10)  # One node reached twice.
    assert not walk(compose("- []\n- []\n- {}\n- {}\n"), 10)  # Distinct empty nodes.
    assert not walk(compose("a: &x 1\nb: *x\n"), 10)  # A shared scalar is not a collection.
    assert not walk(compose("x\n"), 0)


def test_bytes_and_streams_go_to_pure_ruamel(fake_c: type[_FakeCParser]):
    """ruamel reads bytes and streams too; they bypass the guard and the C attempt."""
    assert from_yaml_string(cast(Any, b"a: 1\n")) == {"a": 1}
    assert from_yaml_string(cast(Any, StringIO("a: 1\n"))) == {"a": 1}
    assert fake_c.built == 0


@requires_c
def test_bytes_and_streams_read_the_same_with_the_extension(spies: dict[str, list[str]]):
    assert from_yaml_string(cast(Any, b"a: 1\n")) == {"a": 1}
    assert from_yaml_string(cast(Any, StringIO("a: 1\n"))) == {"a": 1}
    assert spies["c"] == [] and len(spies["pure"]) == 2


# ---- The build gate ----------------------------------------------------------------------


def test_the_c_parser_counts_as_checked_only_for_the_derived_build_and_releases(
    monkeypatch: pytest.MonkeyPatch,
):
    checked = yaml_util._ruamel_is_checked  # pyright: ignore[reportPrivateUsage]
    assert checked((0, 18, 10)) and checked((0, 19, 1)) and checked((0, 19, 99))
    assert not checked((0, 17, 40)) and not checked((0, 20, 0)) and not checked((1, 0, 0))

    monkeypatch.setattr(yaml_util, "_installed_libyaml_version", lambda: CHECKED_LIBYAML_VERSION)
    assert yaml_util._c_parser_is_checked() is checked(ruamel.yaml.version_info)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(yaml_util, "_installed_libyaml_version", lambda: "0.2.5")
    assert not yaml_util._c_parser_is_checked()  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(yaml_util, "_installed_libyaml_version", lambda: None)
    assert not yaml_util._c_parser_is_checked()  # pyright: ignore[reportPrivateUsage]


def test_no_libyaml_version_without_the_extension(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(yaml_util, "_CParser", None)
    assert yaml_util._installed_libyaml_version() is None  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(yaml_util, "_CParser", _FakeCParser)  # A class without a C module.
    assert yaml_util._installed_libyaml_version() is None  # pyright: ignore[reportPrivateUsage]


@requires_c
@pytest.mark.usefixtures("pure_switch")
def test_the_installed_extension_is_the_checked_build():
    """CI installs the extension; a clib release with another libyaml must fail here, so that
    the search behind the guards is rerun before the gate is widened."""
    assert yaml_util._installed_libyaml_version() == CHECKED_LIBYAML_VERSION  # pyright: ignore[reportPrivateUsage]
    assert yaml_util._C_PARSER_CHECKED  # pyright: ignore[reportPrivateUsage]
    assert yaml_parser_mode() == "c-first"


@requires_c
def test_an_unchecked_build_reports_pure_and_keeps_libyaml_out(
    spies: dict[str, list[str]], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(yaml_util, "_C_PARSER_CHECKED", False)
    assert yaml_parser_mode() == "pure"
    assert from_yaml_string(ORDINARY[0]) == read_pure(ORDINARY[0])
    assert spies == {"c": [], "pure": [ORDINARY[0]]}


# ---- Equivalence sweep -------------------------------------------------------------------

ALPHABET = [
    " ", "\n", "\r", "\t", ":", "-", "?", "[", "]", "{", "}", ",", "#", "&", "*", "!", "|",
    ">", "'", '"', "%", "@", "`", ".", "a", "0", "\\", "\x85", "\u2028", "\ufeff", "~", "<",
]  # fmt: skip
SLOT = "\x00"
TEMPLATES = [
    SLOT, f"k: {SLOT}", f"k: [{SLOT}]", f"k: {{{SLOT}}}", f"- {SLOT}", f"k: |\n  {SLOT}\n",
    f"{SLOT}\nk: v\n", f"k:\n  {SLOT}\n", f'k: "{SLOT}"', f"k: '{SLOT}'", f"? {SLOT}\n: v\n",
    f"k: !{SLOT} v", f"&{SLOT} a", f"a: &x 1\nb: *{SLOT}", f"k: a{SLOT}b", f"[a{SLOT}b]",
    f"k: {SLOT}\n...\n", f"---{SLOT}\nk: v\n", f"k: >{SLOT}\n  t\n", f"{SLOT}k: v\n",
    f"k: [a, {SLOT}]", f"k: [{SLOT}: 1]", f'k: ["a"{SLOT}]', f"a: 1\n{SLOT}b: 2\n",
]  # fmt: skip


def _short_texts() -> Iterator[str]:
    for size in (0, 1):
        for chars in itertools.product(ALPHABET, repeat=size):
            for template in TEMPLATES:
                yield template.replace(SLOT, "".join(chars))


def _repo_texts() -> list[str]:
    """YAML the repository itself holds: test string constants, tracked files' frontmatter,
    and tracked YAML files."""
    texts: list[str] = []
    for path in sorted((REPO / "tests").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                texts.append(node.value)
    listed = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout.split()
    for name in listed:
        path = REPO / name
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix in (".yml", ".yaml", ".cff"):
            texts.append(path.read_text(encoding="utf-8"))
        frontmatter = fmf_read_frontmatter_raw(path)[0]
        if frontmatter:
            texts.append(frontmatter)
    texts.extend(
        to_yaml_string(value, typ=typ)
        for value in (SAFE_DUMP_VALUE, {"a": None, "b": [1, {"c": "x: y"}], "d": "l1\nl2"})
        for typ in ("rt", "safe")
    )
    return texts


def _mutations(texts: list[str], per_text: int, seed: int) -> Iterator[str]:
    rng = random.Random(seed)
    for text in texts:
        for _ in range(per_text if text else 0):
            i = rng.randrange(len(text) + 1)
            char = rng.choice(ALPHABET)
            yield [
                text[:i] + char + text[i:],
                text[:i] + text[i + 1 :],
                text[:i] + char + text[i + 1 :],
            ][rng.randrange(3)]


def _sweep_corpus() -> list[str]:
    seeds = (
        _repo_texts()
        + list(ROUTED.values())
        + list(NATURAL_C_FAILURES.values())
        + list(FLOW_COLON)
        + ORDINARY
    )
    small = [text for text in seeds if len(text) <= 4000]
    corpus = seeds + list(_short_texts()) + list(_mutations(small, 25, seed=20261024))
    return list(dict.fromkeys(corpus))


@requires_c
def test_c_first_pure_switch_and_independent_pure_reading_agree_on_every_text(
    monkeypatch: pytest.MonkeyPatch,
):
    corpus = _sweep_corpus()
    assert len(corpus) > 5000
    monkeypatch.delenv(PURE_ENV, raising=False)
    c_first = [outcome(from_yaml_string, text) for text in corpus]
    monkeypatch.setenv(PURE_ENV, "1")
    switched = [outcome(from_yaml_string, text) for text in corpus]
    independent = [outcome(read_pure, text) for text in corpus]

    differing = [text for text, a, b in zip(corpus, c_first, independent, strict=True) if a != b]
    assert differing == []
    assert switched == independent
    # The corpus exercises libyaml, not just the guards: most texts are read by it.
    assert sum(not needs_pure_parser(text) for text in corpus) > len(corpus) // 2


@requires_c
def test_c_first_agrees_with_a_process_that_cannot_import_the_extension(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    corpus = [text for text in _sweep_corpus() if "\ud800" not in text]
    monkeypatch.delenv(PURE_ENV, raising=False)
    here = [repr(outcome(from_yaml_string, text)) for text in corpus]
    corpus_file = tmp_path / "corpus.json"
    corpus_file.write_text(json.dumps(corpus), encoding="utf-8")
    code = (
        "import sys, json; sys.modules['_ruamel_yaml'] = None\n"
        f"sys.path.insert(0, {str(Path(__file__).parent)!r})\n"
        "from test_c_parser import outcome\n"
        "import ruamel.yaml.main\n"
        "assert ruamel.yaml.main.CParser is None\n"
        "from frontmatter_format import from_yaml_string\n"
        "corpus = json.loads(open(sys.argv[1], encoding='utf-8').read())\n"
        "print(json.dumps([repr(outcome(from_yaml_string, t)) for t in corpus]))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code, str(corpus_file)], capture_output=True, text=True, check=True
    )
    there = json.loads(out.stdout)
    assert [text for text, a, b in zip(corpus, here, there, strict=True) if a != b] == []
