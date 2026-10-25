"""
Check that this environment reads YAML with the parser a CI entry claims to test.

A suite that silently ran with the other parser would pass without testing what the
entry says it tests, so each CI entry runs this first and fails closed:

    uv run python devtools/check_yaml_parser.py c-first
    FRONTMATTER_FORMAT_PURE_YAML=1 uv run python devtools/check_yaml_parser.py pure
    uv run python devtools/check_yaml_parser.py c-first --ruamel 0.18.10
"""

from __future__ import annotations

import argparse
import sys

import ruamel.yaml

from frontmatter_format import yaml_parser_mode

SUCCESS_EXIT_CODE = 0
FAILURE_EXIT_CODE = 1


def check(
    expected_mode: str, expected_ruamel: str | None, mode: str, ruamel_version: str
) -> list[str]:
    """
    The problems with an environment whose reader reports `mode` on ruamel.yaml
    `ruamel_version`, against what the CI entry expects. Empty when it matches.
    """
    problems: list[str] = []
    if mode != expected_mode:
        problems.append(f"yaml_parser_mode() is {mode!r}, expected {expected_mode!r}")
    if expected_ruamel is not None and ruamel_version != expected_ruamel:
        problems.append(f"ruamel.yaml is {ruamel_version}, expected {expected_ruamel}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    parser.add_argument("mode", choices=["c-first", "pure"], help="the parser this entry tests")
    parser.add_argument("--ruamel", help="the exact ruamel.yaml version this entry tests")
    args = parser.parse_args(argv)

    mode = yaml_parser_mode()
    ruamel_version = ruamel.yaml.__version__
    print(
        f"yaml_parser_mode(): {mode}; ruamel.yaml {ruamel_version}; Python {sys.version.split()[0]}"
    )
    problems = check(args.mode, args.ruamel, mode, ruamel_version)
    for problem in problems:
        print(problem, file=sys.stderr)
    return FAILURE_EXIT_CODE if problems else SUCCESS_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
