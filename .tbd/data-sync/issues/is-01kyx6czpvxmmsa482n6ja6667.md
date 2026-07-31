---
type: is
id: is-01kyx6czpvxmmsa482n6ja6667
title: Integrate alias-free frontmatter output and portability guidance
kind: task
status: open
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-07-31-deterministic-yaml-output.md
labels: []
dependencies:
  - type: blocks
    target: is-01kyx6d7qxmrbg114tpg29mdgt
parent_id: is-01kyx6cjm1tg2b1rs0416a0y8v
created_at: 2026-07-31T22:58:27.162Z
updated_at: 2026-07-31T22:58:35.388Z
---
Add frontmatter integration coverage showing that mapping metadata expands shared values without anchors while raw YAML strings remain unchanged. Update the README to explain aliases, cycles, and timestamp semantics, recommend ISO strings for portable consumers, and use a quoted ISO timestamp in the introductory example. Do not expose allow_aliases through fmf_write or add a partial JSON-safe mode.
