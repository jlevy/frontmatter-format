---
type: is
id: is-01m5v4xxqefesep73skqhgnrv5
title: "Make long-line wrapping optional (GitHub issue #1)"
kind: feature
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-26T03:44:08.942Z
updated_at: 2026-10-26T03:44:08.942Z
---
GitHub issue https://github.com/jlevy/frontmatter-format/issues/1 (open since 2025-08-29, by an outside user): long string values are wrapped at ruamel's default width (80), which churns diffs (300+ changes in their repo). Example: `to_yaml_string({'test': 'This is a very ... long line.'})` breaks the value onto a second line. The reporter suggests setting `yaml.width`. `new_yaml` sets no width today. Proposal: a `width` option (None for no wrapping) on `new_yaml`, `to_yaml_string`, `dump_yaml`, `write_yaml_file`, `fmf_write` and `fmf_insert_frontmatter`, defaulting to the current behavior; reply on the issue when it lands. Size S-M.
