---
type: is
id: is-01m5sxjv266rmhvkp2nmw380ta
title: "PR #9 Qodo 4371461985: fuzz script accepts zero batch, nonpositive jobs and negative counts"
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T16:16:31.302Z
updated_at: 2026-10-25T16:16:32.011Z
closed_at: 2026-10-25T16:16:32.011Z
close_reason: "fixed in 3f2b343: count >= 0, --batch >= 1 and --jobs >= 1 enforced by argparse types before batching or pool construction."
resolution: null
duplicate_of: null
---
Low (Qodo). devtools/yaml_parser_fuzz.py. https://github.com/jlevy/frontmatter-format/pull/9#discussion_r4371461985. Found by the discovery sweep at d965df6.
