from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from ruamel.yaml.representer import RepresenterError

from frontmatter_format import YamlSerializationError
from frontmatter_format.key_sort import custom_key_sort
from frontmatter_format.yaml_util import (
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
