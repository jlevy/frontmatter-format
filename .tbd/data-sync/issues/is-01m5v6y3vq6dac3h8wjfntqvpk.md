---
type: is
id: is-01m5v6y3vq6dac3h8wjfntqvpk
title: A NEL (U+0085) in a string value reads back as a space, with or without frontmatter
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T04:19:12.375Z
updated_at: 2026-10-26T05:17:58.421Z
closed_at: 2026-10-26T05:17:58.421Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head f3ef992, CI run 40273179324: all 12 jobs pass; Qodo: no findings on f3ef992), commit f3ef992. new_yaml's per-instance representer class now has _EscapingRepresenter as a base. It overrides represent_scalar to force double quotes for any scalar holding NEL, LS, PS or CR, which ruamel writes as \N, \L, \P and \r. This covers values, keys, ScalarString types and stringify_unknown. ruamel's shared classes are not patched: test_line_break_escaping_stays_with_new_yaml_instances checks that a plain YAML() still writes NEL raw.

  Round trips, each failing before the fix:
  - test_line_break_characters_in_values_round_trip: NEL, LS, PS, CR and CRLF x rt/safe x C-first/pure.
  - test_line_break_characters_in_keys_and_other_scalars_round_trip.
  - test_line_break_characters_in_metadata_values_round_trip: the 5 characters x 6 styles x raw/dict/insert x C-first/pure. In C-first mode it asserts there was no pure re-read.
  - The NEL exception was removed from test_writers_round_trip_dict_metadata_with_separators.

  Byte equality: test_strings_without_line_break_characters_keep_their_output_bytes compares output with and without the step over 3,000+ strings, as values, list items and keys, rt and safe. A separate check against main's code (dd2409a) gave 0 differences across 27,435 strings and 164,610 documents, on both ruamel 0.19.1 and 0.18.10.

  Code-point fuzz: every BMP code point and every 97th astral one, in 6 templates, through both writers and both readers. Only one failure class remains: a string holding "\n" plus one of 63 C0/C1 control characters is written as a literal block that raises ReaderError on read. That also happens on main and is loud, not silent. Filed as fmf-jrtu.
resolution: null
duplicate_of: null
---
Found while fixing fmf-uj5a (PR #15). The frontmatter writers now keep a NEL on its line, but the YAML layer still loses it: ruamel 0.19.1 writes `{"a": "x\x85y"}` as `a: 'x\x85  y'` (NEL raw in a single-quoted scalar) and reads that back as `{"a": "x y"}`, in both C-first and pure mode. So `from_yaml_string(to_yaml_string(v)) != v`, and `fmf_write`/`fmf_read` give the same result. LS and PS round-trip; VT, FF and FS/GS/RS are escaped and round-trip. A related case: `"x\r\ny"` is written as a literal block scalar with a raw CRLF and reads back as `"x\ny"`.

Possible fix in yaml_util.py (after the yaml_util gate PR lands): have the str representer use double-quoted style, which escapes NEL as `\N` and CR as `\r`, for strings that contain U+0085 or a CR. Tests should round-trip each through to_yaml_string/from_yaml_string and through fmf_write/fmf_read (see `test_writers_round_trip_dict_metadata_with_separators`, which allows NEL as the one exception today). Size S.
