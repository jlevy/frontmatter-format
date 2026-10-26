"""
Shared fixtures.
"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from ruamel.yaml import YAML

from frontmatter_format import yaml_util
from frontmatter_format.yaml_util import PURE_YAML_ENV, yaml_parser_mode


@pytest.fixture(params=["c-first", "pure"])
def yaml_reader(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Each test runs with the C-first reader and with the pure reader. In c-first mode it
    also checks that libyaml's reading was kept, with no pure re-read."""
    if request.param == "pure":
        monkeypatch.setenv(PURE_YAML_ENV, "1")
        yield "pure"
        return
    monkeypatch.delenv(PURE_YAML_ENV, raising=False)
    if yaml_parser_mode() != "c-first":
        pytest.skip("ruamel's checked C parser is not installed")
    pure_reads: list[str] = []
    real_load_pure: Callable[..., Any] = yaml_util._load_pure  # pyright: ignore[reportPrivateUsage]

    def spy_load_pure(yaml: YAML, text: Any) -> Any:
        pure_reads.append(text)
        return real_load_pure(yaml, text)

    monkeypatch.setattr(yaml_util, "_load_pure", spy_load_pure)
    yield "c-first"
    assert pure_reads == []
