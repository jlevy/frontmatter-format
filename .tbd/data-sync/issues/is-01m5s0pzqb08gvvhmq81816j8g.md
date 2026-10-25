---
type: is
id: is-01m5s0pzqb08gvvhmq81816j8g
title: "PR #9 B4: deep nesting segfaults in the C composer before the depth bound applies"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:51:58.443Z
updated_at: 2026-10-25T16:12:22.013Z
closed_at: 2026-10-25T16:12:22.013Z
close_reason: "fixed in 5c03725: _nesting_bound (flow openers + indicator chain + 2*indent) routes texts that may nest past _C_SCAN_DEPTH=1000 to pure ruamel; subprocess tests at 30k flow, 40k dash, 40k question, 100k flow assert RecursionError not a crash."
resolution: null
duplicate_of: null
---
High. src/frontmatter_format/yaml_util.py:217-229. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. Bounded depth pre-scan; subprocess test at 30k/40k/100k levels.
