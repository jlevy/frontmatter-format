---
type: is
id: is-01m5v4xr0qhfq8j8dnk4c6bsk0
title: Writers reset the target's file mode (a 0755 script becomes 0644)
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:03.094Z
updated_at: 2026-10-26T04:36:48.360Z
closed_at: 2026-10-26T04:36:48.360Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head cc3e4ed, CI run 40268954420: all 12 jobs pass) for fmf_write, fmf_insert_frontmatter and fmf_strip_frontmatter (commits cd5d831 and 20f8168). The new _atomic_write.atomic_write_text copies the replaced file's mode onto the temp file before os.replace. A new file keeps 0o666 less the umask, because the temp file is created with open(..., "x") rather than mkstemp's 0600. On a filesystem that refuses chmod, the write still happens with the default mode (Qodo's finding, fixed in 20f8168). Tests: test_writers_keep_existing_file_mode (3 writers x 0755/0700/0600/0640/0444; all 15 failed on main), test_fmf_write_gives_new_file_the_umask_default_mode, and test_writers_still_write_where_chmod_is_refused. The probe now shows 0o755 after insert, strip and write. write_yaml_file is in yaml_util.py, which was outside this PR's write set: follow-up fmf-xi4b.
resolution: null
duplicate_of: null
---
`fmf_write`, `fmf_insert_frontmatter`, `fmf_strip_frontmatter` and `write_yaml_file` write a new temp file and `os.replace` it over the target, so the target takes the temp file's umask-default mode. A script with hash-style frontmatter loses its executable bit.

Reproduction (a9c3dc0, umask 022): chmod 0755 a file with `#---` frontmatter; after insert, strip or `fmf_write` its mode is 0644; a 0600 YAML file is 0644 after `write_yaml_file`.

Fix: when the target exists, copy its mode to the temp file before the replace (`shutil.copymode`), with a test per writer. Ownership and symlink targets are out of scope unless the fix is trivial. Size S.
