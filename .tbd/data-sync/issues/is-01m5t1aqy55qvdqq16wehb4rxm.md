---
type: is
id: is-01m5t1aqy55qvdqq16wehb4rxm
title: "PR #9 D4: no CI entry runs without the extension installed"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t1apgk247f0502qqasce3m
created_at: 2026-10-25T17:22:00.260Z
updated_at: 2026-10-25T17:29:03.723Z
closed_at: 2026-10-25T17:29:03.723Z
close_reason: "fixed in d23eff1: pure entries sync with --no-install-package ruamel-yaml-clib and run with uv run --no-sync; CI log confirms yaml_parser_mode(): pure and 127 passed, 185 skipped."
resolution: null
duplicate_of: null
---
Low. Review D. .github/workflows/ci.yml pure entries: --no-install-package ruamel-yaml-clib + uv run --no-sync.
