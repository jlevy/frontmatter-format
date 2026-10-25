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
import random
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
from ruamel.yaml.emitter import Emitter, RoundTripEmitter
from ruamel.yaml.parser import Parser, RoundTripParser

from frontmatter_format import fmf_read, fmf_read_frontmatter, fmf_read_frontmatter_raw, yaml_util
from frontmatter_format.yaml_util import (
    add_default_yaml_customizer,
    from_yaml_string,
    new_yaml,
    read_yaml_file,
    to_yaml_string,
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

    def spy_c(text: str) -> Any:
        calls["c"].append(text)
        return load_with_c(text)

    def spy_pure(text: str) -> Any:
        calls["pure"].append(text)
        return load_pure(text)

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
    # Anchors, tags and markers.
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
    assert spies == {"c": [text], "pure": [text]}  # A shared collection goes back to pure.


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


# ---- The switch and the report -----------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "mode"),
    [(None, "c-first"), ("", "c-first"), ("0", "c-first"), ("1", "pure"), ("yes", "pure")],
)
def test_switch_values(value: str | None, mode: str, monkeypatch: pytest.MonkeyPatch):
    from frontmatter_format import PURE_YAML_ENV, yaml_parser_mode

    assert PURE_YAML_ENV == PURE_ENV
    monkeypatch.setattr(yaml_util, "_CParser", _FakeCParser)
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
    from frontmatter_format._libyaml_guard import needs_pure_parser

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
