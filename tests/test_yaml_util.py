from pathlib import Path

import pytest

from frontmatter_format.key_sort import custom_key_sort
from frontmatter_format.yaml_util import (
    YamlTyp,
    from_yaml_string,
    read_yaml_file,
    to_yaml_string,
    write_yaml_file,
)


@pytest.mark.parametrize("typ", ["rt", "safe"])
def test_yaml_output_does_not_depend_on_shared_object_identity(typ: YamlTyp):
    shared = {"metric": 7}
    no_sharing = {"first": {"metric": 7}, "second": {"metric": 7}}
    sharing = {"first": shared, "second": shared}

    assert no_sharing == sharing
    expected = to_yaml_string(no_sharing, typ=typ)
    actual = to_yaml_string(sharing, typ=typ)

    assert actual == expected
    assert "&id" not in actual
    assert "*id" not in actual


@pytest.mark.parametrize("typ", ["rt", "safe"])
def test_yaml_output_preserves_aliases_required_for_recursive_data(typ: YamlTyp):
    recursive: dict[str, object] = {}
    recursive["self"] = recursive

    rendered = to_yaml_string(recursive, typ=typ)
    loaded = from_yaml_string(rendered)

    assert "&id" in rendered
    assert "*id" in rendered
    assert loaded["self"] is loaded


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
