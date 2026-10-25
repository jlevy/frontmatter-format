---
type: is
id: is-01m5t1saf6tvqhx8d40yywx0bc
title: "PR #9 Qodo 4371707142: fuzz search loop duplicates check's comparison"
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5t1apgk247f0502qqasce3m
created_at: 2026-10-25T17:29:57.990Z
updated_at: 2026-10-25T17:31:12.756Z
closed_at: 2026-10-25T17:31:12.756Z
close_reason: "fixed in 9d1ff14: compare() helper shared by check and check_all; test covers the search loop."
resolution: null
duplicate_of: null
---
Low (Qodo, maintainability). devtools/yaml_parser_fuzz.py check_all vs check. https://github.com/jlevy/frontmatter-format/pull/9#discussion_r4371707142. Found by the sweep at d23eff1.
