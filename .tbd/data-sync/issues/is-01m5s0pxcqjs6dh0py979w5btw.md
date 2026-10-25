---
type: is
id: is-01m5s0pxcqjs6dh0py979w5btw
title: "PR #8 A3: threaded test costs 55% of suite runtime; replace with deterministic mid-dump test"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vgrwbab3j2vxkn9q61r
created_at: 2026-10-25T07:51:56.055Z
updated_at: 2026-10-25T16:12:20.180Z
closed_at: 2026-10-25T16:12:20.180Z
close_reason: "fixed in 71e934a: threaded test replaced by the deterministic mid-dump reproduction (fails on main with c: {}, passes in about 1 ms)."
resolution: null
duplicate_of: null
---
Low. tests/test_yaml_util.py:201-224. Review A: https://github.com/jlevy/frontmatter-format/pull/8#pullrequestreview-5641789923.
