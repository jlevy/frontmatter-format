#!/usr/bin/env python3
"""
Differential search: the C-first reader against pure ruamel, where the guards let libyaml run.

`from_yaml_string` reads a text with libyaml only when `_libyaml_guard.needs_pure_parser`
finds none of the shapes on which libyaml is known to accept what pure ruamel rejects, or
to read a different value. That guard list is empirical, so it has to be searched again
after any ruamel, `ruamel.yaml.clib` or libyaml bump. This script is that search: it
generates block and flow documents with tags, anchors, aliases, explicit keys, block scalar
headers, comments, markers and directives, mutates them, mixes in short random strings,
sweeps every three-character string from a YAML alphabet through a set of templates, and
compares the library's C-first reading with pure ruamel's for every text the guard lets
through. A divergence is a text libyaml read to a value that pure ruamel rejects or reads
differently; the fix is a new guard, never a change to the pure result.

Run it from the repo root with the C extension installed (the dev group installs it):

    uv run python devtools/yaml_parser_fuzz.py 200000
    uv run python devtools/yaml_parser_fuzz.py 1000000 --seed 7 --jobs 4
    uv run python devtools/yaml_parser_fuzz.py --exhaustive
    uv run python devtools/yaml_parser_fuzz.py 100000 --corpus docs README.md

Exit status is 1 when any divergence is found, 2 without a usable C parser. The count is
split into batches of `--batch` texts, one seed each. With `--corpus`, texts are mutations
of the frontmatter blocks and YAML files found under the given paths. The unit tests in
`tests/test_c_parser.py` run a small deterministic corpus of the same kind on every CI run;
this script is the larger search behind them.

Pairs this search has been run on with no divergence: ruamel.yaml 0.19.1 with
ruamel.yaml.clib 0.2.15 (CPython 3.10 and 3.13, Linux) and ruamel.yaml 0.18.10 with
ruamel.yaml.clib 0.2.15 (CPython 3.12, Linux). Both report libyaml 0.1.7. Rerun it, and
widen `CHECKED_LIBYAML_VERSION` or `CHECKED_RUAMEL_VERSIONS` only afterwards, when either
package moves.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import itertools
import math
import multiprocessing
import random
import sys
import warnings
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

import ruamel.yaml
from ruamel.yaml.parser import Parser

from frontmatter_format import fmf_split_frontmatter, yaml_util
from frontmatter_format._libyaml_guard import needs_pure_parser
from frontmatter_format.yaml_util import new_yaml

Outcome = tuple[Any, ...]


def canon(value: Any) -> Any:
    """A comparable form of a loaded value: types, key order, float bits and sharing."""
    ids: dict[int, int] = {}

    def go(v: Any) -> Any:
        if isinstance(v, (dict, list, tuple, set, frozenset)):
            key: int = id(cast(object, v))
            if key in ids:
                return ("ref", ids[key])
            ids[key] = len(ids)
            if isinstance(v, dict):
                items = cast(dict[Any, Any], v).items()
                return ("dict", tuple((go(k), go(x)) for k, x in items))
            members = cast(Iterable[Any], v)
            if isinstance(v, (set, frozenset)):
                return ("set", tuple(sorted(repr(go(x)) for x in members)))
            return (type(cast(object, v)).__name__, tuple(go(x) for x in members))
        if isinstance(v, float):
            return ("float", "nan" if math.isnan(v) else v.hex())
        if isinstance(v, (datetime, date)):
            return (type(v).__name__, repr(v), str(getattr(v, "tzinfo", None)))
        return (type(v).__name__, repr(v))

    return go(value)


def pure_outcome(text: str) -> Outcome:
    yaml = new_yaml()
    yaml.Parser = Parser
    try:
        return ("value", canon(yaml.load(text)))
    except RecursionError:
        return ("error", "RecursionError")
    except Exception as exc:
        return ("error", type(exc).__name__, str(exc))


def c_first_outcome(text: str) -> Outcome | None:
    """The reading the library keeps from libyaml, or None when it would fall back to pure."""
    value = yaml_util._load_with_c(new_yaml(), text)  # pyright: ignore[reportPrivateUsage]
    if value is yaml_util._C_FAILED:  # pyright: ignore[reportPrivateUsage]
        return None
    return ("value", canon(value))


def check(text: str) -> tuple[str, Outcome, Outcome] | None:
    """A divergence for `text`, or None. Only a kept C reading can differ from pure ruamel."""
    if needs_pure_parser(text):
        return None
    if yaml_util._nesting_bound(text) > yaml_util._C_SCAN_DEPTH:  # pyright: ignore[reportPrivateUsage]
        return None
    c_reading = c_first_outcome(text)
    if c_reading is None:
        return None
    pure_reading = pure_outcome(text)
    if c_reading != pure_reading:
        return (text, c_reading, pure_reading)
    return None


# ---- Generators ---------------------------------------------------------------------------

PLAIN_CHARS = "abcxyz019 -_.:/?#@!&*%,[]{}|>'\"`~=+$^()\\é\U0001f600"

WORDS = [
    "a", "b c", "x:y", "yes", "No", "on", "OFF", "y", "n", "012", "0o12", "0x1f", "0b101",
    "1_000", "190:20:30", "1e3", "1E3", "1.5e+3", ".5", "+.inf", "-.Inf", ".NaN", "~", "null",
    "Null", "NULL", "true", "True", "TRUE", "=", "<<", "2001-12-14t21:59:43.10-05:00",
    "2002-12-14", "-1", "+1", "0", "-0", "00", "08", "0.", "1.", "1,000", "12:30", "http://x/y",
    "a#b", "a #b", "-x", "?x", ":x", "x:", "x -", "é", "中文", "\U0001f600", "...", "---x",
    "a  b", "a\\b", "@", "%", "`", "!", "&", "*", "|", ">",
]  # fmt: skip

TAGS = ["!!str", "!!int", "!", "!foo", "!!map", "!!seq", "!<tag:yaml.org,2002:str>", "!!set",
        "!!binary", "!e!x", "!!omap", "!!pairs", "!!null", "!!bool", "!!float", "!!timestamp"]  # fmt: skip

BLOCK_HEADERS = ["|", ">", "|-", ">+", "|2", ">1-", "|+", "|#c", "| #c", ">-  ", "|  #c", "|+2"]

MUTATION_CHARS = list(" \n\r:-?[]{},#&*!|>'\"%@`.a0\\~<é\x85 ﻿\t")

ALPHABET3 = list(" \n\r:-?[]{},#&*!|>'\"%.a\\")
"""The alphabet of the exhaustive three-character sweep."""

TEMPLATES3 = [
    "{s}", "k: {s}\n", "[{s}]", "{{{s}}}", "- {s}\n", "k: |\n  {s}\n", "{s}\nk: v\n",
    "? {s}\n: v\n", "k: &a {s}\n", "k: [a, {s}]\n", "k: {{a: {s}}}\n", '["a"{s}]',
    "k: [{s}:x]\n", "[{s}, b]", "k: !!str {s}\n", "--- {s}\n",
]  # fmt: skip
"""Where each three-character string is inserted; `{s}` is the slot."""


class Generator:
    """Seeded block and flow documents that mix every shape the two scanners disagree on."""

    rng: random.Random

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def plain(self) -> str:
        rng = self.rng
        if rng.random() < 0.5:
            return rng.choice(WORDS)
        text = "".join(rng.choice(PLAIN_CHARS) for _ in range(rng.randint(1, 8)))
        return text.strip() or "a"

    def scalar(self, indent: int, flow: bool) -> str:
        rng = self.rng
        roll = rng.random()
        if roll < 0.45:
            return self.plain()
        if roll < 0.6:
            body = "".join(rng.choice("ab :#'\\\"\nx-[]{},é") for _ in range(rng.randint(0, 6)))
            return '"' + body.replace('"', '\\"') + '"'
        if roll < 0.7:
            body = "".join(rng.choice("ab :#\"\nx-[]{},''") for _ in range(rng.randint(0, 6)))
            return "'" + body.replace("'", "''") + "'"
        if roll < 0.8 and not flow:
            header = rng.choice(BLOCK_HEADERS)
            pad = " " * (indent + rng.choice([1, 2, 3]))
            lines = [
                pad[: rng.randint(0, len(pad))]
                + rng.choice(["x", "#y", " z", "", "a: b", "- c", "..."])
                for _ in range(rng.randint(1, 4))
            ]
            return header + "\n" + "\n".join(lines)
        return rng.choice(WORDS)

    def props(self) -> str:
        rng = self.rng
        out: list[str] = []
        if rng.random() < 0.15:
            out.append(rng.choice(TAGS))
        if rng.random() < 0.15:
            out.append("&" + rng.choice(["a", "b", "x1", "a-b", "a_b"]))
        return " ".join(out) + (" " if out else "")

    def flow(self, depth: int) -> str:
        rng = self.rng
        if depth > 3 or rng.random() < 0.4:
            if rng.random() < 0.12:
                return "*" + rng.choice(["a", "b", "x1"])
            return self.props() + self.scalar(0, True)
        items: list[str] = []
        is_map = rng.random() < 0.5
        for _ in range(rng.randint(0, 4)):
            if is_map or rng.random() < 0.2:
                sep = rng.choice([": ", ":", " : ", ":\n ", " :"])
                key = "" if rng.random() < 0.1 else self.flow(depth + 1)
                if rng.random() < 0.15:
                    key = "? " + key
                items.append(key + sep + self.flow(depth + 1))
            else:
                items.append(self.flow(depth + 1))
        body = rng.choice([", ", ",", " , ", ",\n  ", " ,"]).join(items)
        if rng.random() < 0.1:
            body += ","
        return ("{" + body + "}") if is_map else ("[" + body + "]")

    def block(self, indent: int, depth: int) -> str:
        rng = self.rng
        pad = " " * indent
        lines: list[str] = []
        is_seq = rng.random() < 0.35
        for _ in range(rng.randint(1, 4)):
            if rng.random() < 0.08:
                lines.append(pad + "#" + self.plain())
            prefix = pad + ("- " if is_seq else "")
            if not is_seq:
                key = self.props() + (self.plain() if rng.random() < 0.8 else self.flow(2))
                if rng.random() < 0.08:
                    key = "? " + key + "\n" + pad
                prefix += key + rng.choice([": ", ":", ":  "])
            roll = rng.random()
            if depth < 3 and roll < 0.3:
                child = indent + (rng.choice([0, 1, 2, 2, 4]) if not is_seq else 2)
                lines.append(prefix.rstrip() + "\n" + self.block(child, depth + 1))
            elif roll < 0.55:
                lines.append(prefix + self.flow(0))
            elif roll < 0.62:
                lines.append(prefix + "*" + rng.choice(["a", "b", "x1"]))
            else:
                lines.append(prefix + self.props() + self.scalar(indent, False))
            if rng.random() < 0.08:
                lines[-1] += rng.choice([" # c", "  #c", "#c"])
        return "\n".join(lines)

    def document(self) -> str:
        rng = self.rng
        head = rng.choice(
            ["", "", "", "---\n", "--- ", "# c\n", "\n", "--- # c\n", "%YAML 1.2\n---\n"]
        )
        body = self.block(0, 0) if rng.random() < 0.8 else self.flow(0)
        tail = rng.choice(["\n", "", "\n...\n", "\n\n", " \n", "\r\n", "\n... # c\n"])
        text = head + body + tail
        if rng.random() < 0.15:
            text = text.replace("\n", rng.choice(["\r\n", "\r"]))
        return text

    def short(self) -> str:
        return "".join(self.rng.choice(MUTATION_CHARS) for _ in range(self.rng.randint(1, 8)))

    def mutate(self, text: str, count: int) -> str:
        rng = self.rng
        for _ in range(count):
            i = rng.randrange(len(text) + 1)
            op = rng.randrange(4)
            char = rng.choice(MUTATION_CHARS)
            if op == 0:
                text = text[:i] + char + text[i:]
            elif op == 1:
                text = text[:i] + text[i + 1 :]
            elif op == 2:
                text = text[:i] + char + text[i + 1 :]
            else:
                j = rng.randrange(len(text) + 1)
                text = text[:i] + text[min(i, j) : max(i, j)] + text[i:]
        return text

    def texts(self, count: int, corpus: list[str]) -> Iterator[str]:
        """`count` texts: short strings, documents and their mutations, or corpus mutations."""
        rng = self.rng
        for _ in range(count):
            if corpus:
                yield self.mutate(rng.choice(corpus), rng.randint(1, 4))
                continue
            roll = rng.random()
            if roll < 0.2:
                yield self.short()
            elif roll < 0.6:
                yield self.document()
            else:
                yield self.mutate(self.document(), rng.randint(1, 3))


# ---- Jobs -----------------------------------------------------------------------------------

Divergences = list[tuple[str, Outcome, Outcome]]


def search(job: tuple[int, int, list[str]]) -> tuple[int, Divergences]:
    seed, count, corpus = job
    warnings.simplefilter("ignore")
    found: Divergences = []
    for text in Generator(random.Random(seed)).texts(count, corpus):
        result = check(text)
        if result is not None:
            found.append(result)
    return count, found


def exhaustive(job: tuple[int, int]) -> tuple[int, Divergences]:
    low, high = job
    warnings.simplefilter("ignore")
    found: Divergences = []
    checked = 0
    for chars in itertools.islice(itertools.product(ALPHABET3, repeat=3), low, high):
        slot = "".join(chars)
        for template in TEMPLATES3:
            checked += 1
            result = check(template.format(s=slot))
            if result is not None:
                found.append(result)
    return checked, found


def corpus_texts(roots: list[str]) -> list[str]:
    """The frontmatter blocks and YAML files under `roots`, as seeds for mutation."""
    texts: list[str] = []
    for root in roots:
        paths = [Path(root)] if Path(root).is_file() else sorted(Path(root).rglob("*"))
        for path in paths:
            if path.suffix in (".yaml", ".yml"):
                texts.append(path.read_text(encoding="utf-8", errors="replace"))
            elif path.suffix in (".md", ".txt", ".html", ".css", ".py"):
                content = path.read_text(encoding="utf-8", errors="replace")
                raw, _content_offset, _metadata_offset = fmf_split_frontmatter(
                    content, strict=False
                )
                if raw:
                    texts.append(raw)
    return [text for text in dict.fromkeys(texts) if 0 < len(text) <= 6000]


def results(worker: Any, jobs: list[Any], workers: int | None) -> Iterator[tuple[int, Divergences]]:
    if workers == 1:
        yield from map(worker, jobs)
        return
    with multiprocessing.Pool(workers) as pool:
        yield from pool.imap_unordered(worker, jobs)


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("count", type=int, nargs="?", default=0, help="how many texts to generate")
    parser.add_argument("--seed", type=int, default=0, help="first seed; each batch uses the next")
    parser.add_argument("--batch", type=int, default=5000, help="texts per worker batch")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: CPUs)")
    parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="also sweep every three-character string from the alphabet through the templates",
    )
    parser.add_argument(
        "--corpus", nargs="*", default=[], metavar="PATH", help="mutate the YAML found under PATH"
    )
    args = parser.parse_args(argv)

    if not yaml_util._c_parser_active():  # pyright: ignore[reportPrivateUsage]
        message = "no usable C parser: ruamel.yaml.clib is not installed, is not the checked build, or is turned off"
        print(message, file=sys.stderr)
        return 2

    corpus = corpus_texts(args.corpus)
    if args.corpus and not corpus:
        print("no YAML found under the corpus paths", file=sys.stderr)
        return 2

    sizes = [args.batch] * (args.count // args.batch)
    if args.count % args.batch:
        sizes.append(args.count % args.batch)
    jobs: list[Any] = [(args.seed + index, size, corpus) for index, size in enumerate(sizes)]
    total = 0
    found: dict[str, tuple[Outcome, Outcome]] = {}
    for checked, divergences in results(search, jobs, args.jobs):
        total += checked
        for text, c_reading, pure_reading in divergences:
            found.setdefault(text, (c_reading, pure_reading))
    exhaustive_total = 0
    if args.exhaustive:
        combos = len(ALPHABET3) ** 3
        step = max(1, combos // 64)
        ranges = [(low, min(low + step, combos)) for low in range(0, combos, step)]
        for checked, divergences in results(exhaustive, ranges, args.jobs):
            exhaustive_total += checked
            for text, c_reading, pure_reading in divergences:
                found.setdefault(text, (c_reading, pure_reading))

    libyaml = yaml_util._installed_libyaml_version()  # pyright: ignore[reportPrivateUsage]
    clib = _distribution_version("ruamel.yaml.clib")
    last_seed = args.seed + max(len(jobs), 1) - 1
    print(
        f"ruamel.yaml {ruamel.yaml.__version__}, ruamel.yaml.clib {clib} (libyaml {libyaml}), "
        + f"Python {sys.version.split()[0]}, seeds {args.seed}-{last_seed}"
    )
    print(
        f"generated texts: {total}  exhaustive texts: {exhaustive_total}  "
        + f"corpus seeds: {len(corpus)}  divergences: {len(found)}"
    )
    for text, (c_reading, pure_reading) in sorted(found.items(), key=lambda kv: len(kv[0]))[:40]:
        print(repr(text))
        print("   C   :", repr(c_reading)[:200])
        print("   pure:", repr(pure_reading)[:200])
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
