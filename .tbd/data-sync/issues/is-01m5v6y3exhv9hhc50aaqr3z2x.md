---
type: is
id: is-01m5v6y3exhv9hhc50aaqr3z2x
title: write_yaml_file keeps the file mode and fixed temp name; apply the fmf-mkor and fmf-roi5 fix there
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T04:19:11.964Z
updated_at: 2026-10-26T04:19:11.964Z
---
fmf-mkor and fmf-roi5 were fixed in PR #15 for fmf_write, fmf_insert_frontmatter and fmf_strip_frontmatter only. `write_yaml_file` is in src/frontmatter_format/yaml_util.py, which a separate PR (the libyaml gate and regex change) is editing, so #15 left it alone.

Still true on the #15 branch (cd5d831): a 0600 YAML file is 0644 after `write_yaml_file`, and `a.yaml`, `a.yml` and `a` all use the temp file `a.yml.tmp` (`path.with_suffix(".yml.tmp")`), so concurrent writers to those siblings or to one target can collide.

Fix: once the yaml_util PR lands, write through `frontmatter_format._atomic_write.atomic_write_text(path, "yaml")` (unique temp file beside the target, exclusive create, mode copied from the replaced file, os.replace, cleanup on error), and add tests matching `test_writers_keep_existing_file_mode` and `test_writers_use_unique_temp_files_beside_the_target`. Size S.
