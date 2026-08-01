---
type: is
id: is-01kyxcayt9xs3ef5pk3q9r2mgg
title: Harden CI and PyPI publishing for v0.4.0
kind: task
status: open
priority: 1
version: 2
labels: []
dependencies:
  - type: blocks
    target: is-01kyxcb78kscjyy123r2k1kb8b
parent_id: is-01kyxcakkwcfhqxpvqf258c9a1
created_at: 2026-08-01T00:42:12.168Z
updated_at: 2026-08-01T00:42:20.818Z
---
Use frozen installs and UV_EXCLUDE_NEWER, make lint checks non-mutating, prevent untagged workflow_dispatch publishing, validate installed artifacts, constrain build dependencies, SHA-pin actions, and establish a protected release gate.
