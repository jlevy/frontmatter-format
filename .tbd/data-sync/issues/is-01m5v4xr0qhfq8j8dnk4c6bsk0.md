---
type: is
id: is-01m5v4xr0qhfq8j8dnk4c6bsk0
title: Writers reset the target's file mode (a 0755 script becomes 0644)
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:03.094Z
updated_at: 2026-10-26T03:44:03.094Z
---
`fmf_write`, `fmf_insert_frontmatter`, `fmf_strip_frontmatter` and `write_yaml_file` write a new temp file and `os.replace` it over the target, so the target takes the temp file's umask-default mode. A script with hash-style frontmatter loses its executable bit.

Reproduction (a9c3dc0, umask 022): chmod 0755 a file with `#---` frontmatter; after insert, strip or `fmf_write` its mode is 0644; a 0600 YAML file is 0644 after `write_yaml_file`.

Fix: when the target exists, copy its mode to the temp file before the replace (`shutil.copymode`), with a test per writer. Ownership and symlink targets are out of scope unless the fix is trivial. Size S.
