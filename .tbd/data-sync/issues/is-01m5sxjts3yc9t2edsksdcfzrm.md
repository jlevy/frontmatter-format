---
type: is
id: is-01m5sxjts3yc9t2edsksdcfzrm
title: "PR #9 Qodo 4371461984: fuzz script never checks corpus seeds unmutated; corpus-only run checks nothing"
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T16:16:31.010Z
updated_at: 2026-10-25T16:16:31.707Z
closed_at: 2026-10-25T16:16:31.707Z
close_reason: "fixed in 3f2b343: corpus seeds checked once unmutated before mutations and counted in the report; corpus-only runs check the files; nothing-to-search is an argument error."
resolution: null
duplicate_of: null
---
Medium (Qodo). devtools/yaml_parser_fuzz.py. https://github.com/jlevy/frontmatter-format/pull/9#discussion_r4371461984. Found by the discovery sweep at d965df6.
