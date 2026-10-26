---
type: is
id: is-01m5v4xpyzpnebafnr34e722kd
title: fmf_write and fmf_insert_frontmatter split YAML with str.splitlines(), so an LS or NEL in a value reads back as a space
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:02.015Z
updated_at: 2026-10-26T03:44:02.015Z
---
`fmf_write` and `fmf_insert_frontmatter` split the YAML text with `str.splitlines()` (src/frontmatter_format/frontmatter_format.py, `for line in frontmatter_str.splitlines()`), which also breaks at U+2028, U+2029, U+0085, \x0b, \x0c and \x1c-\x1e. ruamel writes LS and NEL raw inside a quoted scalar, so the written file gets a real line break there, and the value reads back changed, with no error.

Reproduction (a9c3dc0): `fmf_write(p, "body\n", {"a": "x y"})` then `fmf_read(p)[1]` returns `{'a': 'x y'}`; same for "\x85" and for `fmf_insert_frontmatter`. Raw-string metadata `'a: "x\x0cy"\n'` is written as `'a: "x\ny"'` (FF, FS likewise).

Fix: split on "\n" only (to_yaml_string emits "\n" line breaks), keeping a final line without a newline, and add round-trip tests for each separator. Size S.
