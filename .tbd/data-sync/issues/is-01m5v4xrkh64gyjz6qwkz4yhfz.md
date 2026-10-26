---
type: is
id: is-01m5v4xrkh64gyjz6qwkz4yhfz
title: "Writers use fixed temp names: concurrent writes to one target race, and write_yaml_file gives a.yaml, a.yml and a the same a.yml.tmp"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:03.696Z
updated_at: 2026-10-26T04:36:48.700Z
closed_at: 2026-10-26T04:36:48.699Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head cc3e4ed, CI run 40268954420: all 12 jobs pass) for the three frontmatter writers (commit cd5d831). Each temp file is {name}.fmf.{write|insert|strip}.{8 hex}.tmp beside the target, created exclusively with open(..., "x"), then moved into place with os.replace. It is removed on any error, and the mode fix (fmf-mkor) is applied before the replace. Tests: test_writers_use_unique_temp_files_beside_the_target, test_writers_leave_other_writers_temp_files_alone, test_concurrent_fmf_write_to_one_target (8 threads x 25 writes; on main it raised FileNotFoundError 7 times), and test_fmf_insert_frontmatter_failure_leaves_file_and_no_temp. The cycle test now checks that the directory is left empty. write_yaml_file's shared a.yml.tmp: follow-up fmf-xi4b.
resolution: null
duplicate_of: null
---
Every writer uses a temp name fixed by the target: `f"{path}.fmf.write.tmp"`, `.fmf.insert.tmp`, `.fmf.strip.tmp`, and in `write_yaml_file` `path.with_suffix(".yml.tmp")`, which gives `a.yaml`, `a.yml` and `a` the same `a.yml.tmp`. Two writers to one target (or to those siblings) share a temp file: one can `os.replace` the other's half-written file into place, or its cleanup can delete the other's temp file so that writer's replace fails.

Fix: create the temp file with `tempfile.mkstemp(dir=path.parent, prefix=..., suffix=".tmp")` (or NamedTemporaryFile(delete=False)) in the target directory, keeping the replace and the cleanup on error. Combine with the mode fix (sibling bead). Size S-M.
