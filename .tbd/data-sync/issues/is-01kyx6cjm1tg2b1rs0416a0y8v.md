---
type: is
id: is-01kyx6cjm1tg2b1rs0416a0y8v
title: "Spec: Deterministic, alias-free YAML output"
kind: epic
status: in_progress
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-31-deterministic-yaml-output.md
labels: []
dependencies: []
child_order_hints:
  - is-01kyx6cseewb3vmqwae183mf45
  - is-01kyx6czpvxmmsa482n6ja6667
  - is-01kyx6d7qxmrbg114tpg29mdgt
created_at: 2026-07-31T22:58:13.760Z
updated_at: 2026-07-31T23:06:14.425Z
---
Implement GitHub issue #4 according to the approved plan: make mapping-based YAML output independent of shared Python object identity, report cycles explicitly, preserve an opt-in for full YAML aliases, and document timestamp portability without adding a partial JSON-safe mode.
