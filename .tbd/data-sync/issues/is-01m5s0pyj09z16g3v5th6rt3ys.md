---
type: is
id: is-01m5s0pyj09z16g3v5th6rt3ys
title: "PR #9 B1: guard regexes backtrack catastrophically (ReDoS on # banners, space lines)"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:51:57.248Z
updated_at: 2026-10-25T16:12:21.106Z
closed_at: 2026-10-25T16:12:21.106Z
close_reason: "fixed in 5c03725: _ROOT_BLOCK_SCALAR comment branch ends only at a line break; space-line rule finds space-only lines first and checks the one line before each, backward search bounded at the previous match start (not end, which was quadratic on consecutive space-only lines); Python 3.10 compatible; growth test (1,000 vs 100,000 units, best of five, limit 1,000x, subprocess deadline) on twelve families; # usage: a | b reaches libyaml. Confirmed: the old guard times out on the families; the fixed one is linear."
resolution: null
duplicate_of: null
---
Blocker. src/frontmatter_format/_libyaml_guard.py:60-62 (_ROOT_BLOCK_SCALAR), :53/:144 (_BLOCK_SPACE_LINE). Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. Linear-time, Python 3.10 compatible; growth-ratio regression tests.
