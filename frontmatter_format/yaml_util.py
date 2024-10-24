"""
YAML file storage. Wraps ruamel.yaml with a few extra features.
"""

import os
from io import StringIO
from typing import Any, Callable, Dict, Optional, TextIO, Type

from ruamel.yaml import Representer, YAML

KeySort = Callable[[str], Any]


def none_or_empty_dict(val: Any) -> bool:
    return val is None or val == {}


_default_representers: Dict[Type[Any], Callable[[Representer, Any], Any]] = {}


def add_default_yaml_representer(type: Type[Any], represent: Callable[[Representer, Any], Any]):
    """
    Add a default representer for a type.
    """
    global _default_representers
    _default_representers[type] = represent


def new_yaml(
    key_sort: Optional[KeySort] = None,
    suppress_vals: Optional[Callable[[Any], bool]] = none_or_empty_dict,
    stringify_unknown: bool = False,
    typ: str = "safe",
) -> YAML:
    """
    Configure a new YAML instance with custom settings.

    If just using this for pretty-printing values, can set `stringify_unknown` to avoid
    RepresenterError for unexpected types.

    For input, `typ="safe"` is safest. For output, consider using `typ="rt"` for better
    control of string formatting (e.g. style of long strings).
    """
    yaml = YAML(typ=typ)
    yaml.default_flow_style = False  # Block style dictionaries.

    suppr = suppress_vals or (lambda v: False)

    # Ignore None values in output. Sort keys if key_sort is provided.
    def represent_dict(dumper, data):
        if key_sort:
            data = {k: data[k] for k in sorted(data.keys(), key=key_sort)}
        return dumper.represent_dict({k: v for k, v in data.items() if not suppr(v)})

    yaml.representer.add_representer(dict, represent_dict)

    # Use YAML block style for strings with newlines.
    def represent_str(dumper, data):
        style = "|" if "\n" in data else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

    yaml.representer.add_representer(str, represent_str)

    # Add other default representers.
    for type, representer in _default_representers.items():
        yaml.representer.add_representer(type, representer)

    if stringify_unknown:

        def represent_unknown(dumper, data):
            return dumper.represent_str(str(data))

        yaml.representer.add_representer(None, represent_unknown)

    if key_sort:
        yaml.representer.sort_base_mapping_type_on_output = False

    return yaml


def from_yaml_string(yaml_string: str) -> Any:
    """
    Read a YAML string into a Python object.
    """
    return new_yaml().load(yaml_string)


def read_yaml_file(filename: str) -> Any:
    """
    Read YAML file into a Python object.
    """
    with open(filename, "r") as f:
        return new_yaml().load(f)


def to_yaml_string(
    value: Any, key_sort: Optional[KeySort] = None, stringify_unknown: bool = False
) -> str:
    """
    Convert a Python object to a YAML string.
    """
    stream = StringIO()
    new_yaml(key_sort=key_sort, stringify_unknown=stringify_unknown, typ="rt").dump(value, stream)
    return stream.getvalue()


def dump_yaml(
    value: Any, stream: TextIO, key_sort: Optional[KeySort] = None, stringify_unknown: bool = False
):
    """
    Write a Python object to a YAML stream.
    """
    new_yaml(key_sort=key_sort, stringify_unknown=stringify_unknown, typ="rt").dump(value, stream)


def write_yaml_file(
    value: Any, filename: str, key_sort: Optional[KeySort] = None, stringify_unknown: bool = False
):
    """
    Write the given value to the YAML file, creating it atomically.
    """
    temp_filename = f"{filename}.yml.tmp"  # Same directory with a temporary suffix.
    try:
        with open(temp_filename, "w", encoding="utf-8") as f:
            dump_yaml(value, f, key_sort, stringify_unknown=stringify_unknown)
        os.replace(temp_filename, filename)
    except Exception as e:
        try:
            os.remove(temp_filename)
        except FileNotFoundError:
            pass
        raise e
