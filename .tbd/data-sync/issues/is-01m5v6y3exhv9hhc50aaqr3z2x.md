---
type: is
id: is-01m5v6y3exhv9hhc50aaqr3z2x
title: write_yaml_file keeps the file mode and fixed temp name; apply the fmf-mkor and fmf-roi5 fix there
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T04:19:11.964Z
updated_at: 2026-10-26T05:17:57.997Z
closed_at: 2026-10-26T05:17:57.996Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head f3ef992, CI run 40273179324: all 12 jobs pass; Qodo: no findings on f3ef992), commit f3ef992. write_yaml_file serializes first and then writes through atomic_write_text(path, "yaml"): a unique {name}.fmf.yaml.{8 hex}.tmp beside the target, created exclusively, the replaced file's mode copied where chmod is allowed (otherwise the umask default), then os.replace, with cleanup on error. Tests, in tests/test_yaml_util.py: test_write_yaml_file_keeps_existing_file_mode (0755/0700/0600/0640/0444; all 5 failed before), test_write_yaml_file_uses_unique_temp_files_beside_each_target (a.yaml, a.yml and a; failed before), test_write_yaml_file_leaves_another_writers_temp_file_alone (a.yml.tmp; failed before), test_concurrent_write_yaml_file_to_sibling_targets (6 threads x 25; failed before with FileNotFoundError), test_write_yaml_file_gives_new_file_the_umask_default_mode, test_write_yaml_file_still_writes_where_chmod_is_refused, and test_write_yaml_file_failure_leaves_target_and_no_temp.
resolution: null
duplicate_of: null
---
fmf-mkor and fmf-roi5 were fixed in PR #15 for fmf_write, fmf_insert_frontmatter and fmf_strip_frontmatter only. `write_yaml_file` is in src/frontmatter_format/yaml_util.py, which a separate PR (the libyaml gate and regex change) is editing, so #15 left it alone.

Still true on the #15 branch (cd5d831): a 0600 YAML file is 0644 after `write_yaml_file`, and `a.yaml`, `a.yml` and `a` all use the temp file `a.yml.tmp` (`path.with_suffix(".yml.tmp")`), so concurrent writers to those siblings or to one target can collide.

Fix: once the yaml_util PR lands, write through `frontmatter_format._atomic_write.atomic_write_text(path, "yaml")` (unique temp file beside the target, exclusive create, mode copied from the replaced file, os.replace, cleanup on error), and add tests matching `test_writers_keep_existing_file_mode` and `test_writers_use_unique_temp_files_beside_the_target`. Size S.
