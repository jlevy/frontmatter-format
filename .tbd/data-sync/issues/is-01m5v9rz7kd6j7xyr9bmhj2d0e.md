---
type: is
id: is-01m5v9rz7kd6j7xyr9bmhj2d0e
title: A string with a newline and a C0/C1 control character is written as an unreadable literal block
kind: bug
status: closed
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T05:08:49.522Z
updated_at: 2026-10-26T06:17:01.290Z
closed_at: 2026-10-26T06:17:01.289Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15, commit ad66892 (CI run 40276266774: all 12 jobs pass; Qodo: no findings on ad66892). _ESCAPE_ONLY_CHARACTERS in yaml_util.py now covers every character outside YAML 1.2's c-printable set, surrogates included, plus NEL, LS, PS and CR. Those strings are written double-quoted with standard escapes, and tab stays out of the set.

  Tests, 1,074 cases of which failed on f3ef992:
  - test_escaped_characters_in_metadata_values_round_trip: all 63 characters x 6 frontmatter styles x raw/dict/insert x C-first/pure.
  - test_escaped_characters_in_values_round_trip and test_escaped_characters_in_keys_and_other_scalars_round_trip.
  - test_escaped_characters_use_yaml_escapes.
  - test_escaping_non_printable_characters_changes_only_output_that_did_not_read_back: the 63 characters and 4 surrogates, 6 templates, values and keys, rt/safe, every ScalarString type. Every changed output failed to read back before, and every new output reads back exactly.

  Bytes: test_strings_without_escaped_characters_keep_their_output_bytes passes, and a check against main's code gave 0 differences across 27,426 strings and 164,556 documents, on ruamel 0.19.1 and 0.18.10.

  Fuzz: 0 failures over 139,158 code points x 6 templates, through both writers and both readers (378 at f3ef992). A full scan of all 1,112,064 non-surrogate code points x 3 templates x 2 readers also has 0 failures (63 at f3ef992).

  Gate at ad66892: lint-check clean; test 1,659 passed; slow 1 passed; pure 1,659 passed; floor locally 1,657 passed plus 2 existing skips.
resolution: null
duplicate_of: null
---
Found by the code-point fuzz for fmf-jm7i (PR #15). It also happens on main at dd2409a, so #15 did not cause it. Values such as {"k": "a\nb\x00c"} are dumped by to_yaml_string as `k: |-\n  a\n  b\x00c\n`, because represent_str asks for a literal block whenever the text has "\n" and the emitter honours that even though the text has a character YAML does not allow raw. Reading it back raises ReaderError (FmFormatError through fmf_read), in both C-first and pure mode. So write_yaml_file, fmf_write and fmf_insert_frontmatter succeed but leave a file that cannot be read. The failure is loud on read, not a silent value change. The affected characters are C0 except tab, LF and CR, plus DEL and C1 except NEL: 63 code points (0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f, 0x7f, 0x80-0x84, 0x86-0x9f, plus two more that the full scan will name). Without a "\n" those characters are already double-quoted and escaped, and they round-trip.

Fix: extend `_ESCAPE_ONLY_CHARACTERS` in yaml_util.py (the escape step on the per-instance representer from #15) to the characters ruamel cannot write raw. Output bytes then change only for strings whose output today is unreadable; single-line strings with these characters are already written double-quoted. Size S. Held out of #15 because the brief limited byte changes to strings with NEL, LS, PS or CR.

## Notes

Full scan (all 1,112,064 non-surrogate code points, value "a\nb<c>c", ruamel 0.19.1, PR #15 head f3ef992): exactly 63 fail, all raising ReaderError, none silently changed. They are 0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f, 0x7f, 0x80-0x84, 0x86-0x9f, U+FFFE and U+FFFF. A batched fuzz of every BMP code point and every 97th astral one, in 6 templates ("x{c}y", "a\nb{c}c", "{c}", " {c} ", "{c}\n", "{c}{c}\n\n"), through to_yaml_string/from_yaml_string and fmf_write/fmf_read in yaml and hash styles, C-first and pure, found no other failures.
