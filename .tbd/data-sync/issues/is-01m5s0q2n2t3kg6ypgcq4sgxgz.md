---
type: is
id: is-01m5s0q2n2t3kg6ypgcq4sgxgz
title: "PR #9 B11 (Qodo 4369814217): default customizers run twice on every fallback read"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:52:01.442Z
updated_at: 2026-10-25T16:12:24.119Z
closed_at: 2026-10-25T16:12:24.118Z
close_reason: "fixed in 5c03725: one new_yaml() instance per read; the C attempt restores the parser (and, after a3ba9ca, the constructor class) and removes ruamel's loader attributes; tests: customizers run once in all four outcomes, Qodo's toggling customizer raises DuplicateKeyError as one pure load does."
resolution: null
duplicate_of: null
---
Low (Qodo: Medium). src/frontmatter_format/yaml_util.py:206-210,217-233. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. Qodo inline comment: https://github.com/jlevy/frontmatter-format/pull/9#discussion_r4369814217. Build one instance per read.
