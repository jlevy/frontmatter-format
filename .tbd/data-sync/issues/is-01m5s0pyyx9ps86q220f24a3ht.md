---
type: is
id: is-01m5s0pyyx9ps86q220f24a3ht
title: "PR #9 B2: ruamel.yaml 0.18.x: every C-first read raises AttributeError on max_depth"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:51:57.660Z
updated_at: 2026-10-25T16:12:21.359Z
closed_at: 2026-10-25T16:12:21.358Z
close_reason: "fixed in 5c03725 (getattr defaults for version and max_depth; test_accepts_the_c_parser_on_a_handle_without_max_depth) and d965df6 (CI floor job: Python 3.10, ruamel.yaml 0.18.10 with the extension, 239 passed; also 239 passed locally on 0.18.10/3.12)."
resolution: null
duplicate_of: null
---
Blocker. src/frontmatter_format/yaml_util.py:250. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. getattr default; CI leg at the dependency floor.
