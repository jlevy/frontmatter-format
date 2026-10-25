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
