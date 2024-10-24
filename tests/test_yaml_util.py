import os

from frontmatter_format.key_sort import custom_key_sort
from frontmatter_format.yaml_util import read_yaml_file, write_yaml_file


def test_write_yaml_file_with_custom_key_sort():
    os.makedirs("tmp", exist_ok=True)

    file_path = "tmp/test_write_yaml_file.yaml"
    data = {"title": "Test Title", "author": "Test Author", "date": "2022-01-01"}
    priority_keys = ["date", "title"]
    write_yaml_file(data, file_path, key_sort=custom_key_sort(priority_keys))
    read_data = read_yaml_file(file_path)

    # Priority keys should be first.
    assert list(read_data.keys()) == priority_keys + [
        k for k in data.keys() if k not in priority_keys
    ]


def test_write_yaml_file_with_suppress_vals():
    os.makedirs("tmp", exist_ok=True)

    file_path = "tmp/test_write_yaml_file_suppress_vals.yaml"
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
