---
type: is
id: is-01kyxcaykcp4bt72jzt0cx1vsv
title: Resolve v0.4.0 dependency security advisories
kind: chore
status: closed
priority: 1
version: 6
labels: []
dependencies:
  - type: blocks
    target: is-01kyxcb78kscjyy123r2k1kb8b
parent_id: is-01kyxcakkwcfhqxpvqf258c9a1
created_at: 2026-08-01T00:42:11.947Z
updated_at: 2026-08-01T01:11:16.016Z
closed_at: 2026-08-01T01:11:16.012Z
close_reason: Mirrored the Simple Modern uv v0.4.0 development and build constraints, upgraded pytest and Pygments past their advisories, verified every changed package cleared the 14-day cooling period, and passed the complete local validation gate.
---
Mirror the Simple Modern uv v0.4.0 audited development-tool constraints and locked versions, including fixes for pytest GHSA-6w46-j5rx-g56g and Pygments GHSA-5239-wwwm-4pmq. Verify the template release and packages meet the 14-day policy, inspect the lock diff, and run the full matrix.
