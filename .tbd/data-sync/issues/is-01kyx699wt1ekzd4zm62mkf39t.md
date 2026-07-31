---
type: is
id: is-01kyx699wt1ekzd4zm62mkf39t
title: Suppress identity-only YAML anchors in emitted frontmatter
kind: bug
status: closed
priority: 1
version: 2
labels:
  - portability
dependencies: []
created_at: 2026-07-31T22:56:26.521Z
updated_at: 2026-07-31T23:16:25.875Z
closed_at: 2026-07-31T23:16:25.874Z
close_reason: "Implemented in 040383b and PR #5; safe/rt tests, type/lint/build, downstream reproduction, and all PR checks pass."
---
Fix jlevy/frontmatter-format#4: equal acyclic values must serialize identically regardless of Python object sharing. Preserve cyclic-graph serialization through the existing YAML alias mechanism, and cover safe/round-trip dump paths.
