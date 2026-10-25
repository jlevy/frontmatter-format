import pytest

from devtools.check_yaml_parser import FAILURE_EXIT_CODE, SUCCESS_EXIT_CODE, check, main
from frontmatter_format import yaml_parser_mode


def test_matching_mode_and_version_pass():
    assert check("c-first", None, "c-first", "0.19.1") == []
    assert check("pure", "0.18.10", "pure", "0.18.10") == []


def test_the_other_parser_is_a_problem():
    assert check("c-first", None, "pure", "0.19.1") == [
        "yaml_parser_mode() is 'pure', expected 'c-first'"
    ]
    assert check("pure", None, "c-first", "0.19.1") == [
        "yaml_parser_mode() is 'c-first', expected 'pure'"
    ]


def test_another_ruamel_release_is_a_problem():
    assert check("pure", "0.18.10", "pure", "0.19.1") == ["ruamel.yaml is 0.19.1, expected 0.18.10"]
    assert len(check("c-first", "0.18.10", "pure", "0.19.1")) == 2


def test_main_reports_this_environment(capsys: pytest.CaptureFixture[str]):
    mode = yaml_parser_mode()
    other = "pure" if mode == "c-first" else "c-first"
    assert main([mode]) == SUCCESS_EXIT_CODE
    assert main([other]) == FAILURE_EXIT_CODE
    assert main([mode, "--ruamel", "0.0.0"]) == FAILURE_EXIT_CODE
    assert "expected 0.0.0" in capsys.readouterr().err
