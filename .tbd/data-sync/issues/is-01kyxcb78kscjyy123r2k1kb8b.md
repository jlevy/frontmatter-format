---
type: is
id: is-01kyxcb78kscjyy123r2k1kb8b
title: Validate the final v0.4.0 release candidate
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kyxcakkwcfhqxpvqf258c9a1
created_at: 2026-08-01T00:42:20.818Z
updated_at: 2026-08-01T01:15:34.195Z
closed_at: 2026-08-01T01:15:34.190Z
close_reason: "Completed the full local release gate and hosted Python 3.10-3.14 matrix; DeepSource and Bugbot passed, no review threads remain, and PR #7 is cleanly mergeable from current main."
---
After all release blockers close, rerun main CI, full lint/type/test matrix, zero-alert security checks, exact-version wheel/sdist builds, isolated installs, metadata/content inspection, release-note review, tag-to-main verification, and PyPI publication verification.
