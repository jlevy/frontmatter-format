"""
YAML file storage. Wraps ruamel.yaml with a few extra features and
convenience functions.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence, Set
from io import StringIO
from pathlib import Path
from typing import Any, Literal, TextIO

from ruamel.yaml import YAML, Representer

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


def none_or_empty_dict(val: Any) -> bool:
    return val is None or val == {}


YamlCustomizer = Callable[[YAML], None]

_default_yaml_customizers: list[YamlCustomizer] = []


def _container_children(value: Any) -> Iterator[Any] | None:
    if isinstance(value, Mapping):
        return (item for pair in value.items() for item in pair)
    if isinstance(value, (Sequence, Set)) and not isinstance(value, (str, bytes, bytearray)):
        return iter(value)
    return None


def _recursive_container_ids(value: Any) -> set[int]:
    """Return container identities that require aliases to close a cycle."""
    active: set[int] = set()
    complete: set[int] = set()
    recursive: set[int] = set()

    def visit(candidate: Any) -> None:
        children = _container_children(candidate)
        if children is None:
            return

        candidate_id = id(candidate)
        if candidate_id in active:
            recursive.add(candidate_id)
            return
        if candidate_id in complete:
            return

        active.add(candidate_id)
        for child in children:
            visit(child)
        active.remove(candidate_id)
        complete.add(candidate_id)

    visit(value)
    return recursive


def _configure_portable_aliases(yaml: YAML) -> None:
    """Suppress identity-only aliases while retaining aliases required by cycles."""
    representer = yaml.representer
    base_represent = representer.represent
    recursive_ids: set[int] = set()

    def represent(data: Any) -> None:
        recursive_ids.update(_recursive_container_ids(data))
        try:
            base_represent(data)
        finally:
            recursive_ids.clear()

    def ignore_aliases(data: Any) -> bool:
        return id(data) not in recursive_ids

    representer.represent = represent
    representer.ignore_aliases = ignore_aliases


def add_default_yaml_customizer(customizer: YamlCustomizer):
    """
    Customize the default YAML instance by adding a function to configure it.
    """
    _default_yaml_customizers.append(customizer)


def add_default_yaml_representer(type: type[Any], represent: Callable[[Representer, Any], Any]):
    """
    Add a default representer for a type.
    """
    _default_yaml_customizers.append(lambda yaml: yaml.representer.add_representer(type, represent))


def new_yaml(
    key_sort: KeySort[str] | None = None,
    suppress_vals: Callable[[Any], bool] | None = none_or_empty_dict,
    stringify_unknown: bool = False,
    typ: YamlTyp = "safe",
) -> YAML:
    """
    Configure a new YAML instance with custom settings.

    If just using this for pretty-printing values, can set `stringify_unknown` to avoid
    RepresenterError for unexpected types.

    For input, `typ="safe"` is safest. For output, consider using `typ="rt"` for better
    control of string formatting (e.g. style of long strings).

    Repeated references to the same acyclic container are expanded so output depends on
    values rather than Python object identity. Recursive containers retain the aliases
    required to represent the cycle.
    """
    yaml = YAML(typ=typ)
    yaml.default_flow_style = False  # Block style dictionaries.
    _configure_portable_aliases(yaml)

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

    return yaml


def from_yaml_string(yaml_string: str) -> Any:
    """
    Read a YAML string into a Python object.
    """
    return new_yaml().load(yaml_string)


def read_yaml_file(path: str | Path) -> Any:
    """
    Read YAML file into a Python object.
    """
    path = Path(path)
    return new_yaml().load(path.read_text(encoding="utf-8"))


def to_yaml_string(
    value: Any,
    key_sort: KeySort[str] | None = None,
    stringify_unknown: bool = False,
    typ: YamlTyp = "rt",
) -> str:
    """
    Convert a Python object to a YAML string.
    """
    stream = StringIO()
    new_yaml(key_sort=key_sort, stringify_unknown=stringify_unknown, typ=typ).dump(value, stream)
    return stream.getvalue()


def dump_yaml(
    value: Any,
    stream: TextIO,
    key_sort: KeySort[str] | None = None,
    stringify_unknown: bool = False,
    typ: YamlTyp = "rt",
):
    """
    Write a Python object to a YAML stream.
    """
    new_yaml(key_sort=key_sort, stringify_unknown=stringify_unknown, typ=typ).dump(value, stream)


def write_yaml_file(
    value: Any,
    path: str | Path,
    key_sort: KeySort[str] | None = None,
    stringify_unknown: bool = False,
    typ: YamlTyp = "rt",
):
    """
    Write the given value to the YAML file, creating it atomically.
    """
    path = Path(path)
    temp_path = path.with_suffix(".yml.tmp")
    try:
        temp_path.write_text(
            to_yaml_string(value, key_sort, stringify_unknown=stringify_unknown, typ=typ),
            encoding="utf-8",
        )
        temp_path.replace(path)
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise e
