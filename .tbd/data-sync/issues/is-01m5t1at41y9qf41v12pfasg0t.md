---
type: is
id: is-01m5t1at41y9qf41v12pfasg0t
title: "PR #9 E3: documents under the scan bound segfault the C composer on small thread stacks (3.11-3.13)"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t1apgk247f0502qqasce3m
created_at: 2026-10-25T17:22:02.497Z
updated_at: 2026-10-25T17:29:05.649Z
closed_at: 2026-10-25T17:29:05.649Z
close_reason: "fixed in 534c307: _C_SCAN_DEPTH=200, docstring corrected; small-thread-stack subprocess tests at 200 (raw), 190 (reader vs pure, 128 KB and 8 MB) and 600 (RecursionError); skip on 3.10 where pure itself overflows."
resolution: null
duplicate_of: null
---
High. Review E. _C_SCAN_DEPTH=1000 assumes 8 MB stacks; 128 KB threads overflow at about 400.
