---
type: is
id: is-01m5v4xrkh64gyjz6qwkz4yhfz
title: "Writers use fixed temp names: concurrent writes to one target race, and write_yaml_file gives a.yaml, a.yml and a the same a.yml.tmp"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:03.696Z
updated_at: 2026-10-26T03:44:03.696Z
---
Every writer uses a temp name fixed by the target: `f"{path}.fmf.write.tmp"`, `.fmf.insert.tmp`, `.fmf.strip.tmp`, and in `write_yaml_file` `path.with_suffix(".yml.tmp")`, which gives `a.yaml`, `a.yml` and `a` the same `a.yml.tmp`. Two writers to one target (or to those siblings) share a temp file: one can `os.replace` the other's half-written file into place, or its cleanup can delete the other's temp file so that writer's replace fails.

Fix: create the temp file with `tempfile.mkstemp(dir=path.parent, prefix=..., suffix=".tmp")` (or NamedTemporaryFile(delete=False)) in the target directory, keeping the replace and the cleanup on error. Combine with the mode fix (sibling bead). Size S-M.
