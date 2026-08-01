---
type: is
id: is-01kyxerpq3eyrnxq6hq5xfs70g
title: Publish and verify frontmatter-format v0.4.0
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kyxcakkwcfhqxpvqf258c9a1
created_at: 2026-08-01T01:24:39.778Z
updated_at: 2026-08-01T01:28:28.701Z
closed_at: 2026-08-01T01:28:28.700Z
close_reason: "Merged PR #7 at 78e0dd4, published GitHub release v0.4.0, completed trusted-publishing workflow 30677899821, verified the two non-yanked PyPI files (wheel sha256 71d6b416c6b05242d934b6228d2386311f2f9216d4d1d47549e6cadf7963fe76; sdist sha256 dd7bc579b50e12a236c03427826a9af14fd2029e20dcae927e68f7440538e75a), and passed a fresh no-cache PyPI install plus feature smoke test."
---
Merge PR #7, validate the exact merged main commit, create the v0.4.0 GitHub release and tag at that commit, watch the trusted-publishing workflow to completion, and verify PyPI metadata plus a clean isolated install.
