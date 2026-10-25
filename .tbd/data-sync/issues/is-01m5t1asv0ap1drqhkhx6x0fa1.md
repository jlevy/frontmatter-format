---
type: is
id: is-01m5t1asv0ap1drqhkhx6x0fa1
title: "PR #9 E2: verbatim empty tag !<!> on an empty node reads '' from libyaml, None from pure"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t1apgk247f0502qqasce3m
created_at: 2026-10-25T17:22:02.208Z
updated_at: 2026-10-25T17:29:05.394Z
closed_at: 2026-10-25T17:29:05.394Z
close_reason: fixed in 534c307 by the same property rule; !<!> fixtures; verbatim.py 0 of 55 differ.
resolution: null
duplicate_of: null
---
Blocker. Review E. _EMPTY_NON_SPECIFIC_TAG matches only a bare !.
