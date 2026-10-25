---
type: is
id: is-01m5t1ashvzezzekdzzsenbhk1
title: "PR #9 E1: root block scalar with tag/anchor on an earlier line read differently by libyaml"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t1apgk247f0502qqasce3m
created_at: 2026-10-25T17:22:01.915Z
updated_at: 2026-10-25T17:29:05.091Z
closed_at: 2026-10-25T17:29:05.091Z
close_reason: "fixed in 534c307: _NODE_PROPERTY routes every tag, anchor and alias at a token start, replacing the property-specific rules; E1 texts are fixtures; probes/gen/fuzz 0 divergences; 4 of 140 real seeds routed (workflow files)."
resolution: null
duplicate_of: null
---
Blocker. Review E. _ROOT_BLOCK_SCALAR property group accepts only spaces after a property.
