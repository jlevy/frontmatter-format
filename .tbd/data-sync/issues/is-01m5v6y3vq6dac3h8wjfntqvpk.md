---
type: is
id: is-01m5v6y3vq6dac3h8wjfntqvpk
title: A NEL (U+0085) in a string value reads back as a space, with or without frontmatter
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T04:19:12.375Z
updated_at: 2026-10-26T04:19:12.375Z
---
Found while fixing fmf-uj5a (PR #15). The frontmatter writers now keep a NEL on its line, but the YAML layer still loses it: ruamel 0.19.1 writes `{"a": "x\x85y"}` as `a: 'x\x85  y'` (NEL raw in a single-quoted scalar) and reads that back as `{"a": "x y"}`, in both C-first and pure mode. So `from_yaml_string(to_yaml_string(v)) != v`, and `fmf_write`/`fmf_read` give the same result. LS and PS round-trip; VT, FF and FS/GS/RS are escaped and round-trip. A related case: `"x\r\ny"` is written as a literal block scalar with a raw CRLF and reads back as `"x\ny"`.

Possible fix in yaml_util.py (after the yaml_util gate PR lands): have the str representer use double-quoted style, which escapes NEL as `\N` and CR as `\r`, for strings that contain U+0085 or a CR. Tests should round-trip each through to_yaml_string/from_yaml_string and through fmf_write/fmf_read (see `test_writers_round_trip_dict_metadata_with_separators`, which allows NEL as the one exception today). Size S.
