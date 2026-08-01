---
type: is
id: is-01kyxcaz7mq4zdvapesz1rqkay
title: Restrict the v0.4.0 source distribution payload
kind: chore
status: open
priority: 2
version: 2
labels: []
dependencies:
  - type: blocks
    target: is-01kyxcb78kscjyy123r2k1kb8b
parent_id: is-01kyxcakkwcfhqxpvqf258c9a1
created_at: 2026-08-01T00:42:12.595Z
updated_at: 2026-08-01T00:42:20.818Z
---
Configure Hatch sdist include/exclude rules so PyPI does not ship .tbd, agent integrations, workflows, hooks, or arbitrary untracked repository content. Rebuild and inspect both artifacts.
