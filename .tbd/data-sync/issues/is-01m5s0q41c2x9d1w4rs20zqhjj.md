---
type: is
id: is-01m5s0q41c2x9d1w4rs20zqhjj
title: "PR #9 B15: depth walk treats CPython's shared empty tuple as an alias"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:52:02.860Z
updated_at: 2026-10-25T16:12:25.157Z
closed_at: 2026-10-25T16:12:25.156Z
close_reason: "fixed in 5c03725 (empty collections skipped in the value walk) and superseded in a3ba9ca: the check now walks the nodes libyaml composed, where every empty sequence is a distinct node; test_shared_empty_tuples_are_not_taken_for_aliases kept."
resolution: null
duplicate_of: null
---
Suggestion. src/frontmatter_format/yaml_util.py:258-284. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227.
