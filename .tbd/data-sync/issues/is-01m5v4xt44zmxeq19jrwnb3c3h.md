---
type: is
id: is-01m5v4xt44zmxeq19jrwnb3c3h
title: Read-path performance follow-ups after v0.5.0
kind: epic
status: open
priority: 3
version: 7
labels: []
dependencies: []
child_order_hints:
  - is-01m5v4xtjz5jv382d4jhzjh7t5
  - is-01m5v4xv47hg98jaer144766c5
  - is-01m5v4xvmpy8ydabxc1vgq1jc6
  - is-01m5v4xw86qnrfw7vn5pcgg9xg
  - is-01m5v4xwqkcr9vffhw38trzgfk
  - is-01m5v4xx7jbrsagpvr8sz71t13
created_at: 2026-10-26T03:44:05.251Z
updated_at: 2026-10-26T03:44:08.433Z
---
Read-path speed follow-ups after v0.5.0. Measured at a9c3dc0 on CPython 3.14.6, ruamel.yaml 0.19.1, ruamel.yaml.clib 0.2.15. A typical C-first read of a 439-character frontmatter block costs about 680 us; most of it is ruamel's Python constructor and resolver, plus `new_yaml()` per read (about 50 us, part of it ruamel's per-instance plug-in glob in `YAML.__init__`), none of which is a safe quick fix. The first three children are value-identical (same routing decision, same reads); the rest change routing and need the differential search (`devtools/yaml_parser_fuzz.py`) and C-stack tests.
