---
type: is
id: is-01kyxcaykcp4bt72jzt0cx1vsv
title: Resolve v0.4.0 dependency security advisories
kind: chore
status: open
priority: 1
version: 2
labels: []
dependencies:
  - type: blocks
    target: is-01kyxcb78kscjyy123r2k1kb8b
parent_id: is-01kyxcakkwcfhqxpvqf258c9a1
created_at: 2026-08-01T00:42:11.947Z
updated_at: 2026-08-01T00:42:20.818Z
---
Update only the locked pytest and Pygments versions needed to close CVE-2025-71176/GHSA-6w46-j5rx-g56g and CVE-2026-4539/GHSA-5239-wwwm-4pmq. Keep the maintenance diff focused, apply the 14-day policy, audit, and run the full matrix.
