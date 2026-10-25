---
type: is
id: is-01m5s0q2zs2k7cary5x9tq7eky
title: "PR #9 B12: yaml_parser_mode() can report c-first when no read uses libyaml"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:52:01.785Z
updated_at: 2026-10-25T16:12:24.372Z
closed_at: 2026-10-25T16:12:24.372Z
close_reason: "fixed in a3ba9ca: yaml_parser_mode() derives from the reader's predicate (_c_parser_active and _accepts_c_parser(new_yaml())), so a customizer that changes the loader, an unchecked build (B6) or the switch all report pure."
resolution: null
duplicate_of: null
---
Low. src/frontmatter_format/yaml_util.py:176-194. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227.
