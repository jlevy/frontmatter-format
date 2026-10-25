---
type: is
id: is-01m5s0q04bv7qv8qwspwf2gfw8
title: "PR #9 B5: CI never runs the C path or the dependency floor"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:51:58.859Z
updated_at: 2026-10-25T16:12:22.358Z
closed_at: 2026-10-25T16:12:22.358Z
close_reason: "fixed in d965df6: ruamel.yaml.clib>=0.2.15 in the dev group (lock gains only it; cool-off respected), build matrix gains a yaml-parser dimension (c-first and pure per Python 3.10-3.14), floor job on ruamel.yaml 0.18.10, devtools/check_yaml_parser.py fails entries closed, docs/development.md describes it. CI run 40210056106: all 11 jobs green."
resolution: null
duplicate_of: null
---
High. pyproject.toml dev group; .github/workflows/ci.yml. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. Add clib to dev group, pure-switch step, floor job, docs/development.md.
