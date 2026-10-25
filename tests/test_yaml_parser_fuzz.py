"""
The differential search behind the libyaml guards is evidence, so it has tests of its own:
it must find a known divergence when a guard is missing, reject bad arguments, and the
installed (ruamel.yaml, ruamel.yaml.clib) pair must be one it has been run on.
"""

from __future__ import annotations

import re

import pytest

from devtools.yaml_parser_fuzz import (
    SEARCHED_PAIRS,
    Generator,
    check,
    installed_pair,
    kept_reading,
    main,
)
from frontmatter_format import _libyaml_guard
from tests.test_c_parser import LIBYAML_DIFFERS, ORDINARY, requires_c

PRE_B3_FLOW_TOKEN_COLON = re.compile(r":(?<=[ \[{,\r\n]:)(?![ \r\n])")
"""The lookbehind before review B's B3, without `]` and `}`."""


@requires_c
def test_the_search_finds_a_divergence_when_a_guard_is_missing(monkeypatch: pytest.MonkeyPatch):
    assert check("[[]:]") is None
    monkeypatch.setattr(_libyaml_guard, "_FLOW_TOKEN_COLON", PRE_B3_FLOW_TOKEN_COLON)
    found = check("[[]:]")
    assert found is not None
    text, c_reading, pure_reading = found
    assert text == "[[]:]" and c_reading[0] == "value" and pure_reading[0] == "error"


@requires_c
def test_routed_texts_are_never_kept_and_ordinary_texts_are():
    assert all(kept_reading(text) is None for text in LIBYAML_DIFFERS.values())
    assert all(kept_reading(text) is not None for text in ORDINARY)
    assert all(check(text) is None for text in ORDINARY)


def test_the_generator_produces_the_shapes_review_e_found():
    """Properties separated from their node by a line break or comment, and the verbatim
    empty tag, which the first generator never produced."""
    texts = list(Generator(__import__("random").Random(1)).texts(20_000, []))
    assert any(re.search(r"[!&][^ \r\n]*(\r?\n|#)", text) for text in texts)
    assert any("!<!>" in text for text in texts)
    assert any(re.match(r"(?:---|[!&][^\n]*\n|\s)*[|>]", text) for text in texts)


def test_bad_arguments_are_rejected():
    for argv in (["--batch", "0"], ["-5"], ["5", "--jobs", "0"], []):
        with pytest.raises(SystemExit) as excinfo:
            main(argv)
        assert excinfo.value.code == 2


@requires_c
def test_the_installed_pair_has_been_searched():
    """A lock bump to a ruamel.yaml or ruamel.yaml.clib release the search has not covered
    fails here until `devtools/yaml_parser_fuzz.py` is rerun and the pair added."""
    assert installed_pair() in SEARCHED_PAIRS
