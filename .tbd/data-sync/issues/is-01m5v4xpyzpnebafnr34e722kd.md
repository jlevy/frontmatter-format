---
type: is
id: is-01m5v4xpyzpnebafnr34e722kd
title: fmf_write and fmf_insert_frontmatter split YAML with str.splitlines(), so an LS or NEL in a value reads back as a space
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:02.015Z
updated_at: 2026-10-26T04:36:47.675Z
closed_at: 2026-10-26T04:36:47.675Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head cc3e4ed, CI run 40268954420: all 12 jobs pass), commit cd5d831. fmf_write and fmf_insert_frontmatter now split metadata with _split_lines, which breaks only at LF, CRLF and CR. Tests: test_fmf_write_raw_metadata_round_trips_separators (8 separators x 6 styles; raw metadata reads back exactly through fmf_read_raw) and test_writers_round_trip_dict_metadata_with_separators (dict metadata through fmf_write and fmf_insert_frontmatter). 60 of these cases failed on main. Probe after the fix: LS and PS round-trip through write and insert. Raw FF and FS are now written verbatim, and ruamel reports them as invalid YAML instead of the value silently changing. A NEL in a dict value still reads back as a space, because ruamel folds it even without frontmatter (from_yaml_string(to_yaml_string(v)) != v): follow-up fmf-jm7i.
resolution: null
duplicate_of: null
---
`fmf_write` and `fmf_insert_frontmatter` split the YAML text with `str.splitlines()` (src/frontmatter_format/frontmatter_format.py, `for line in frontmatter_str.splitlines()`), which also breaks at U+2028, U+2029, U+0085, \x0b, \x0c and \x1c-\x1e. ruamel writes LS and NEL raw inside a quoted scalar, so the written file gets a real line break there, and the value reads back changed, with no error.

Reproduction (a9c3dc0): `fmf_write(p, "body\n", {"a": "x y"})` then `fmf_read(p)[1]` returns `{'a': 'x y'}`; same for "\x85" and for `fmf_insert_frontmatter`. Raw-string metadata `'a: "x\x0cy"\n'` is written as `'a: "x\ny"'` (FF, FS likewise).

Fix: split on "\n" only (to_yaml_string emits "\n" line breaks), keeping a final line without a newline, and add round-trip tests for each separator. Size S.
