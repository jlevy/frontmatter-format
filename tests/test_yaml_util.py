import ast
import os
import random
import stat
import threading
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, cast

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.constructor import (
    BaseConstructor,
    ConstructorError,
    RoundTripConstructor,
    SafeConstructor,
)
from ruamel.yaml.representer import (
    BaseRepresenter,
    RepresenterError,
    RoundTripRepresenter,
    SafeRepresenter,
)
from ruamel.yaml.scalarstring import (
    DoubleQuotedScalarString,
    FoldedScalarString,
    LiteralScalarString,
    PlainScalarString,
    SingleQuotedScalarString,
)

from frontmatter_format import YamlSerializationError, yaml_util
from frontmatter_format.key_sort import custom_key_sort
from frontmatter_format.yaml_util import (
    YamlTyp,
    dump_yaml,
    from_yaml_string,
    new_yaml,
    read_yaml_file,
    to_yaml_string,
    write_yaml_file,
)


def test_to_yaml_string_is_independent_of_shared_container_identity():
    shared_mapping = {"base_case": 2.0}
    shared_list = ["yaml", "portable"]
    shared_value = {
        "mapping_a": shared_mapping,
        "mapping_b": shared_mapping,
        "list_a": shared_list,
        "list_b": shared_list,
    }
    unshared_value = {
        "mapping_a": {"base_case": 2.0},
        "mapping_b": {"base_case": 2.0},
        "list_a": ["yaml", "portable"],
        "list_b": ["yaml", "portable"],
    }

    for typ in ("rt", "safe"):
        assert to_yaml_string(shared_value, typ=typ) == to_yaml_string(unshared_value, typ=typ)


def test_new_yaml_rejects_cycles_with_actionable_error():
    yaml = new_yaml()
    cyclic_value: dict[str, object] = {}
    cyclic_value["self"] = cyclic_value

    with pytest.raises(
        YamlSerializationError,
        match=r"cyclic object graph.*allow_aliases=True",
    ):
        yaml.dump(cyclic_value, StringIO())


def test_low_level_writers_can_preserve_aliases(tmp_path: Path):
    cyclic_value: dict[str, object] = {}
    cyclic_value["self"] = cyclic_value
    expected = "&id001\nself: *id001\n"

    # Positional calls are deliberate: they verify allow_aliases was appended
    # after typ rather than inserted before existing parameters.
    direct_stream = StringIO()
    new_yaml(None, None, False, "rt", True).dump(cyclic_value, direct_stream)

    helper_stream = StringIO()
    dump_yaml(cyclic_value, helper_stream, None, False, "rt", True)

    output_path = tmp_path / "cyclic.yml"
    write_yaml_file(cyclic_value, output_path, None, False, "rt", True)

    assert direct_stream.getvalue() == expected
    assert to_yaml_string(cyclic_value, None, False, "rt", True) == expected
    assert helper_stream.getvalue() == expected
    assert output_path.read_text(encoding="utf-8") == expected


def test_round_trip_load_expands_authored_anchors_unless_allowed():
    source = "a: &x\n  m: 7\nb: *x\n"

    default_yaml = new_yaml(typ="rt")
    expanded = StringIO()
    default_yaml.dump(default_yaml.load(source), expanded)
    assert expanded.getvalue() == "a:\n  m: 7\nb:\n  m: 7\n"

    preserving_yaml = new_yaml(typ="rt", allow_aliases=True)
    preserved = StringIO()
    preserving_yaml.dump(preserving_yaml.load(source), preserved)
    assert preserved.getvalue() == source


def test_serialization_error_preserves_ruamel_exception_compatibility():
    assert issubclass(YamlSerializationError, RepresenterError)


def test_reader_accepts_aliases_and_timestamps():
    value = from_yaml_string(
        "model_a: &model\n  base_case: 2.0\nmodel_b: *model\ncreated_at: 2024-01-02\n"
    )

    assert value == {
        "model_a": {"base_case": 2.0},
        "model_b": {"base_case": 2.0},
        "created_at": date(2024, 1, 2),
    }
    assert value["model_a"] is value["model_b"]


def test_timestamp_values_and_date_looking_strings_round_trip():
    value = {
        "date_value": date(2024, 1, 2),
        "datetime_value": datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        "date_string": "2024-01-02",
    }

    yaml_string = to_yaml_string(value)

    assert yaml_string == (
        "date_value: 2024-01-02\n"
        "datetime_value: 2024-01-02 03:04:05+00:00\n"
        "date_string: '2024-01-02'\n"
    )
    assert from_yaml_string(yaml_string) == value


def test_write_yaml_file_with_custom_key_sort(tmp_path: Path):
    file_path = tmp_path / "test_write_yaml_file.yaml"
    data = {"title": "Test Title", "author": "Test Author", "date": "2022-01-01"}
    priority_keys = ["date", "title"]
    write_yaml_file(data, file_path, key_sort=custom_key_sort(priority_keys))
    read_data = read_yaml_file(file_path)

    # Priority keys should be first.
    assert list(read_data.keys()) == priority_keys + [
        k for k in data.keys() if k not in priority_keys
    ]


def test_write_yaml_file_with_suppress_vals(tmp_path: Path):
    file_path = tmp_path / "test_write_yaml_file_suppress_vals.yaml"
    data = {
        "title": "Test Title",
        "author": "Test Author",
        "date": "2022-01-01",
        "empty_dict": {},
        "none_value": None,
        "content": "Some content",
    }

    write_yaml_file(data, file_path)

    read_data = read_yaml_file(file_path)

    assert "empty_dict" not in read_data
    assert "none_value" not in read_data

    assert read_data["title"] == "Test Title"
    assert read_data["author"] == "Test Author"
    assert read_data["date"] == "2022-01-01"
    assert read_data["content"] == "Some content"


def _dump(yaml: YAML, value: object) -> str:
    stream = StringIO()
    yaml.dump(value, stream)
    return stream.getvalue()


@pytest.mark.parametrize("typ", ["rt", "safe"])
def test_a_later_instance_does_not_change_an_earlier_instances_output(typ: YamlTyp):
    """Each instance keeps its own representers; building another one cannot rewrite them."""
    keep_everything = new_yaml(suppress_vals=lambda _value: False, typ=typ)
    value: dict[str, Any] = {"kept_null": None, "kept_empty": {}, "text": "x"}
    before = _dump(keep_everything, value)
    new_yaml(typ=typ)  # Default policy: drops None and {}.
    assert _dump(keep_everything, value) == before
    assert "kept_null: null" in before and "kept_empty: {}" in before


def test_a_later_instance_does_not_change_an_earlier_instances_key_order():
    reversed_keys = new_yaml(key_sort=lambda key: tuple(-ord(c) for c in key), typ="rt")
    value = {"a": 1, "b": 2, "c": 3}
    before = _dump(reversed_keys, value)
    new_yaml(typ="rt")
    assert _dump(reversed_keys, value) == before
    assert before.splitlines() == ["c: 3", "b: 2", "a: 1"]


def test_new_yaml_leaves_ruamels_shared_representer_tables_unchanged():
    def table(cls: type) -> dict[Any, Any]:
        return dict(cast(dict[Any, Any], cls.yaml_representers))

    tables = {cls: table(cls) for cls in (RoundTripRepresenter, SafeRepresenter)}
    for typ in ("rt", "safe"):
        new_yaml(suppress_vals=lambda _value: False, typ=typ, stringify_unknown=True)
        new_yaml(typ=typ)
    assert {cls: table(cls) for cls in tables} == tables


def test_building_an_instance_mid_dump_does_not_change_the_rest_of_the_document():
    """The race the fix removes: a default-policy instance built partway through a dump
    used to switch the policy of the rest of the document. One thread reproduces it."""

    class Trigger:
        pass

    def represent_trigger(dumper, _trigger):  # pyright: ignore
        new_yaml(typ="rt")  # Rebuilds the default policy partway through this dump.
        return dumper.represent_str("t")

    writer = new_yaml(suppress_vals=lambda _value: False, typ="rt")
    writer.representer.add_representer(Trigger, represent_trigger)
    value = {"a": {"x": None}, "b": Trigger(), "c": {"x": None}}
    assert _dump(writer, value) == "a:\n  x: null\nb: t\nc:\n  x: null\n"


class _Tagged:
    yaml_tag: str = "!Tagged"
    x: int

    def __init__(self, x: int):
        self.x = x

    @classmethod
    def to_yaml(cls, representer: Any, node: "_Tagged") -> Any:
        return representer.represent_scalar(cls.yaml_tag, str(node.x))

    @classmethod
    def from_yaml(cls, _constructor: Any, node: Any) -> "_Tagged":
        return cls(int(node.value))


@pytest.mark.parametrize("typ", ["rt", "safe"])
def test_constructors_registered_on_an_instance_stay_with_it(typ: YamlTyp):
    """`register_class` registers a constructor as well as a representer; both are private."""

    def table(cls: type) -> dict[Any, Any]:
        return dict(cast(dict[Any, Any], cls.yaml_constructors))

    shared = {cls: table(cls) for cls in (RoundTripConstructor, SafeConstructor)}
    registered = new_yaml(typ=typ)
    registered.register_class(_Tagged)
    loaded = registered.load("!Tagged 7")
    assert isinstance(loaded, _Tagged) and loaded.x == 7
    assert _dump(registered, {"t": _Tagged(7)}) == "t: !Tagged 7\n"

    for other in (new_yaml(typ=typ), YAML(typ=typ)):
        if typ == "safe":
            with pytest.raises(ConstructorError):
                other.load("!Tagged 7")
        else:  # The round-trip loader keeps an unknown tag as a `TaggedScalar`.
            assert not isinstance(other.load("!Tagged 7"), _Tagged)
    assert {cls: table(cls) for cls in shared} == shared


@pytest.mark.parametrize("typ", ["rt", "safe", "full", "base"])
def test_every_typ_builds(typ: YamlTyp):
    """`typ="full"` has no constructor class to subclass; the others have both."""
    yaml = new_yaml(typ=typ)
    assert issubclass(yaml.Representer, BaseRepresenter)
    if typ == "full":
        assert yaml.Constructor is None
    else:
        assert issubclass(yaml.Constructor, BaseConstructor)
        assert yaml.Constructor is not BaseConstructor
    if typ != "base":
        assert _dump(yaml, {"a": 1, "b": ["x"]}) == "a: 1\nb:\n- x\n"


def test_default_representers_still_apply_to_every_new_instance(monkeypatch: pytest.MonkeyPatch):
    class Point:
        x: int

        def __init__(self, x: int):
            self.x = x

    monkeypatch.setattr(yaml_util, "_default_yaml_customizers", [])
    yaml_util.add_default_yaml_representer(
        Point, lambda dumper, point: dumper.represent_scalar("tag:yaml.org,2002:str", f"p{point.x}")
    )
    for typ in ("rt", "safe"):
        assert _dump(new_yaml(typ=typ), {"at": Point(3)}) == "at: p3\n"


# write_yaml_file writes atomically through a unique temp file and keeps the file mode
# (fmf-xi4b, the fmf-mkor and fmf-roi5 fixes for this writer).

needs_posix_modes = pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")


@needs_posix_modes
@pytest.mark.parametrize("mode", [0o755, 0o700, 0o600, 0o640, 0o444])
def test_write_yaml_file_keeps_existing_file_mode(tmp_path: Path, mode: int):
    file_path = tmp_path / "data.yml"
    file_path.write_text("a: 1\n", encoding="utf-8")
    file_path.chmod(mode)

    write_yaml_file({"a": 2}, file_path)

    assert read_yaml_file(file_path) == {"a": 2}
    assert stat.S_IMODE(file_path.stat().st_mode) == mode
    assert list(tmp_path.iterdir()) == [file_path]


@needs_posix_modes
def test_write_yaml_file_gives_new_file_the_umask_default_mode(tmp_path: Path):
    file_path = tmp_path / "new.yaml"
    old_umask = os.umask(0o027)
    try:
        write_yaml_file({"a": 1}, file_path)
    finally:
        os.umask(old_umask)

    assert stat.S_IMODE(file_path.stat().st_mode) == 0o640


def test_write_yaml_file_still_writes_where_chmod_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    file_path = tmp_path / "data.yml"
    file_path.write_text("a: 1\n", encoding="utf-8")

    def refuse_chmod(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "chmod", refuse_chmod)
    write_yaml_file({"a": 2}, file_path)
    monkeypatch.undo()

    assert file_path.read_text(encoding="utf-8") == "a: 2\n"
    assert list(tmp_path.iterdir()) == [file_path]


def test_write_yaml_file_uses_unique_temp_files_beside_each_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # `a.yaml`, `a.yml` and `a` all used `a.yml.tmp` before.
    targets = [tmp_path / "a.yaml", tmp_path / "a.yml", tmp_path / "a"]
    replaced: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def spy_replace(src: Any, dst: Any) -> None:
        replaced.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy_replace)
    for target in targets * 2:
        write_yaml_file({"name": target.name}, target)

    temp_paths = [src for src, _ in replaced]
    assert [dst for _, dst in replaced] == targets * 2
    assert len(set(temp_paths)) == len(temp_paths)
    assert all(src.parent == tmp_path for src in temp_paths)
    assert sorted(tmp_path.iterdir()) == sorted(targets)


def test_write_yaml_file_leaves_another_writers_temp_file_alone(tmp_path: Path):
    other = tmp_path / "a.yml.tmp"  # The fixed temp name earlier releases used.
    other.write_text("another write in progress\n", encoding="utf-8")

    for name in ("a.yaml", "a.yml", "a"):
        write_yaml_file({"name": name}, tmp_path / name)

    assert other.read_text(encoding="utf-8") == "another write in progress\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["a", "a.yaml", "a.yml", "a.yml.tmp"]


def test_concurrent_write_yaml_file_to_sibling_targets(tmp_path: Path):
    targets = [tmp_path / "a.yaml", tmp_path / "a.yml", tmp_path / "a"]
    errors: list[BaseException] = []

    def write_repeatedly(writer: int) -> None:
        try:
            for i in range(25):
                target = targets[(writer + i) % len(targets)]
                write_yaml_file({"writer": writer, "target": target.name}, target)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=write_repeatedly, args=(i,)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    for target in targets:
        assert read_yaml_file(target)["target"] == target.name
    assert sorted(tmp_path.iterdir()) == sorted(targets)


def test_write_yaml_file_failure_leaves_target_and_no_temp(tmp_path: Path):
    file_path = tmp_path / "data.yml"
    file_path.write_text("a: 1\n", encoding="utf-8")
    cyclic: dict[str, Any] = {}
    cyclic["self"] = cyclic

    with pytest.raises(YamlSerializationError):
        write_yaml_file({"cyclic": cyclic}, file_path)

    assert file_path.read_text(encoding="utf-8") == "a: 1\n"
    assert list(tmp_path.iterdir()) == [file_path]


# A string holding NEL, LS, PS, CR or a character outside YAML 1.2's c-printable set is
# written double-quoted with escapes, so it reads back exactly; every other string is
# written as before (fmf-jm7i, fmf-jrtu).

LINE_BREAK_CHARACTERS = {"NEL": "\x85", "LS": "\u2028", "PS": "\u2029", "CR": "\r", "CRLF": "\r\n"}


def _c_printable(cp: int) -> bool:
    """YAML 1.2's `c-printable` production."""
    return (
        cp in (0x09, 0x0A, 0x0D)
        or 0x20 <= cp <= 0x7E
        or cp == 0x85
        or 0xA0 <= cp <= 0xD7FF
        or 0xE000 <= cp <= 0xFFFD
        or 0x10000 <= cp <= 0x10FFFF
    )


CONTROL_CHARACTERS = {
    f"U+{cp:04X}": chr(cp)
    for cp in range(0x10000)
    if not _c_printable(cp) and not 0xD800 <= cp <= 0xDFFF
}
"""The characters outside `c-printable` that UTF-8 can encode: C0 controls but tab, LF and
CR, DEL, C1 controls but NEL, U+FFFE and U+FFFF."""

ESCAPED_CHARACTERS = {**LINE_BREAK_CHARACTERS, **CONTROL_CHARACTERS}

_ESCAPED_SET = (
    frozenset("\x85\u2028\u2029\r")
    | frozenset(CONTROL_CHARACTERS.values())
    | frozenset(chr(cp) for cp in range(0xD800, 0xE000))
)
"""Every single character the writer escapes, surrogates included (CRLF is CR then LF)."""


def _has_escaped_character(text: str) -> bool:
    return not _ESCAPED_SET.isdisjoint(text)


def test_control_characters_are_the_63_outside_c_printable():
    assert len(CONTROL_CHARACTERS) == 63
    assert "\t" not in _ESCAPED_SET and "\n" not in _ESCAPED_SET and "\ufeff" not in _ESCAPED_SET


@pytest.mark.usefixtures("yaml_reader")
@pytest.mark.parametrize("char", ESCAPED_CHARACTERS.values(), ids=ESCAPED_CHARACTERS.keys())
@pytest.mark.parametrize("typ", ["rt", "safe"])
def test_escaped_characters_in_values_round_trip(typ: YamlTyp, char: str):
    value = {
        "inside": f"x{char}y",
        "edges": f"{char}x{char}",
        "alone": char,
        "with_newlines": f"line one\nline two{char}line three\n",
        "long": ("word " * 30) + char + (" word" * 30),
        "list": [f"a{char}b", f"{char}"],
    }

    text = to_yaml_string(value, typ=typ)

    assert not _has_escaped_character(text)
    assert from_yaml_string(text) == value


@pytest.mark.parametrize("char", ESCAPED_CHARACTERS.values(), ids=ESCAPED_CHARACTERS.keys())
def test_escaped_characters_in_keys_and_other_scalars_round_trip(char: str):
    class Unknown:
        def __str__(self) -> str:  # pyright: ignore[reportImplicitOverride]
            return f"unknown{char}object"

    value = {f"key{char}": 1, "nested": {f"{char}": [f"v{char}"]}}
    text = to_yaml_string(value)
    assert not _has_escaped_character(text)
    assert from_yaml_string(text) == value

    # ruamel's round-trip string types keep their own style unless it would lose the value.
    for scalar_type in (
        LiteralScalarString,
        FoldedScalarString,
        SingleQuotedScalarString,
        DoubleQuotedScalarString,
        PlainScalarString,
    ):
        typed = {"a": scalar_type(f"x{char}y\nz")}
        typed_text = to_yaml_string(typed)
        assert not _has_escaped_character(typed_text), scalar_type
        assert from_yaml_string(typed_text) == {"a": f"x{char}y\nz"}, scalar_type

    unknown_text = to_yaml_string({"u": Unknown()}, stringify_unknown=True)
    assert from_yaml_string(unknown_text) == {"u": f"unknown{char}object"}


def test_escaped_characters_use_yaml_escapes():
    line_breaks = "1\x852\u20283\u20294\r5\r\n6"
    assert to_yaml_string({"a": line_breaks}) == 'a: "1\\N2\\L3\\P4\\r5\\r\\n6"\n'
    controls = "\x00\x07\x08\x0b\x0c\x0e\x1b\x1f\x7f\x80\x9f\ufffe\uffff"
    assert to_yaml_string({"a": f"{controls}\ttab\nb"}) == (
        'a: "\\0\\a\\b\\v\\f\\x0E\\e\\x1F\\x7F\\x80\\x9F\\uFFFE\\uFFFF\\ttab\\nb"\n'
    )
    # A tab is printable, so a string whose only special character is a tab keeps
    # ruamel's own output.
    assert to_yaml_string({"a": "x\ty\nz"}) == "a: |-\n  x\ty\n  z\n"


def test_line_break_escaping_stays_with_new_yaml_instances():
    """The escape step is on each instance's own representer class: ruamel's classes and a
    plain ruamel instance keep their output."""
    for typ in ("rt", "safe"):
        new_yaml(typ=typ)
        plain_output = _dump(YAML(typ=typ, pure=True), {"a": "x\x85y"})
        assert "\x85" in plain_output and "\\N" not in plain_output
    for cls in (RoundTripRepresenter, SafeRepresenter):
        assert cls.represent_scalar is BaseRepresenter.represent_scalar


def _without_escape_step(yaml: YAML) -> YAML:
    """The same instance with its representer class's escape step removed: the output
    `new_yaml` gave before the step was added."""
    representer_class = type(yaml.representer)
    representer_class.represent_scalar = BaseRepresenter.represent_scalar  # pyright: ignore
    return yaml


_CORPUS_ALPHABET = (
    "abcxyzABC019 _-.,:;?!#&*|>'\"%@`\\/[]{}()~=+$^<\n\t"
    + "\xa0éüß\u0301—“”‘’☕\ufeff\ud7ff\ue000\ufffd😀\U0010fffd"
)

_CORPUS_WORDS = [
    "", " ", "  ", "yes", "no", "on", "off", "null", "Null", "~", "true", "False", "1",
    "-1", "1.5", "1e3", ".inf", ".nan", "0x1F", "0o17", "2024-01-01", "2024-01-01 10:00:00",
    "12:30", "- a", "a: b", "a:b", "#x", "x #y", "? x", "[a]", "{a: 1}", "&a", "*a", "!t",
    "%TAG", "---", "...", " leading", "trailing ", "multi\nline", "multi\nline\n",
    "trailing newlines\n\n\n", "\n", "\n\n", "\nleading newline", "tab\there", "\ttab first",
    "back\\slash", "quote's", 'double "quote"', "unicode café ☕ 😀", "bom\ufeffhere",
    "x" * 200, ("word " * 40).strip(), "line\n  indented\n\tand tabbed\n",
]  # fmt: skip


def _corpus_strings() -> list[str]:
    """Strings with none of `ESCAPED_CHARACTERS`: hand-picked YAML-special words, every
    string constant in the test suite, and seeded random strings over a wide alphabet of
    printable characters, tab and LF."""
    strings = list(_CORPUS_WORDS)
    for path in sorted(Path(__file__).parent.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.append(node.value)
    rng = random.Random(20261026)
    for _ in range(3000):
        length = rng.choice([1, 2, 3, 5, 8, 13, 40, 90, 150])
        strings.append("".join(rng.choice(_CORPUS_ALPHABET) for _ in range(length)))
    return [s for s in dict.fromkeys(strings) if not _has_escaped_character(s)]


def test_strings_without_escaped_characters_keep_their_output_bytes():
    strings = _corpus_strings()
    assert len(strings) > 3000
    mismatches: list[tuple[str, str, str]] = []
    for typ in ("rt", "safe"):
        writer = new_yaml(typ=typ)
        before = _without_escape_step(new_yaml(typ=typ))
        for s in strings:
            for value in ({"k": s}, [s, {"n": [s]}], {s: 1}):
                out = _dump(writer, value)
                if out != _dump(before, value):
                    mismatches.append((typ, s, out))
    assert mismatches == []


def _dump_or_none(yaml: YAML, value: object) -> str | None:
    try:
        return _dump(yaml, value)
    except Exception:  # ruamel's folded-block emitter can raise on these strings.
        return None


def _reads_back(text: str | None, value: object) -> bool:
    if text is None:
        return False
    try:
        return from_yaml_string(text) == value
    except Exception:
        return False


@pytest.mark.parametrize("typ", ["rt", "safe"])
def test_escaping_non_printable_characters_changes_only_output_that_did_not_read_back(
    typ: YamlTyp,
):
    surrogates = ["\ud800", "\udbff", "\udc00", "\udfff"]
    templates = ["x{c}y", "{c}", " {c} ", "{c}\n", "a\nb{c}c", "line one\nline{c}two\n"]
    kinds: list[type[str]] = [str]
    if typ == "rt":
        kinds += [
            LiteralScalarString,
            FoldedScalarString,
            SingleQuotedScalarString,
            DoubleQuotedScalarString,
            PlainScalarString,
        ]
    writer = new_yaml(typ=typ)
    before = _without_escape_step(new_yaml(typ=typ))
    changed = 0
    for char in [*CONTROL_CHARACTERS.values(), *surrogates]:
        for template in templates:
            text = template.format(c=char)
            for kind in kinds:
                for value, expected in (
                    ({"k": kind(text)}, {"k": text}),
                    ({kind(text): 1}, {text: 1}),
                ):
                    new = _dump_or_none(writer, value)
                    old = _dump_or_none(before, value)
                    assert _reads_back(new, expected), (char, template, kind, new)
                    if new != old:
                        changed += 1
                        assert not _reads_back(old, expected), (char, template, kind, old)
    assert changed > 0
