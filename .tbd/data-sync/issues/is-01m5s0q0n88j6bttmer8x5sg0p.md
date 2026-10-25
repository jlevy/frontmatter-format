---
type: is
id: is-01m5s0q0n88j6bttmer8x5sg0p
title: "PR #9 B6: C-first not gated to the checked libyaml build and ruamel line"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:51:59.400Z
updated_at: 2026-10-25T16:12:22.729Z
closed_at: 2026-10-25T16:12:22.729Z
close_reason: "fixed in 5c03725: CHECKED_LIBYAML_VERSION='0.1.7' and CHECKED_RUAMEL_VERSIONS=((0,18),(0,20)) gate _c_parser_active, mirroring softschema's _portable.py; yaml_parser_mode reports pure outside them; tests for the predicate and for the installed build being the checked one."
resolution: null
duplicate_of: null
---
Medium. src/frontmatter_format/yaml_util.py:158,193-194. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. Mirror softschema CHECKED_LIBYAML_VERSION / CHECKED_RUAMEL_VERSIONS.
