---
type: is
id: is-01m5t1aqm7305pvr2pb5ztsszn
title: "PR #9 D3: build gate admits unsearched (ruamel, clib) pairs; nothing enforces rerunning the search"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t1apgk247f0502qqasce3m
created_at: 2026-10-25T17:21:59.943Z
updated_at: 2026-10-25T17:29:03.451Z
closed_at: 2026-10-25T17:29:03.451Z
close_reason: "fixed in b12fb67: SEARCHED_PAIRS in devtools/yaml_parser_fuzz.py; test_the_installed_pair_has_been_searched fails on an unlisted pair; README states the gate as 'libyaml 0.1.7 on ruamel.yaml 0.18 or 0.19'. Runtime clib-release gating not added (speed cost; CI test keeps the list honest)."
resolution: null
duplicate_of: null
---
Low. Review D. Record searched pairs; CI test fails on an unlisted pair; README wording.
