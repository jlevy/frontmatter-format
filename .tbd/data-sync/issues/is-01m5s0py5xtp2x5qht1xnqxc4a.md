---
type: is
id: is-01m5s0py5xtp2x5qht1xnqxc4a
title: "PR #8 A5: constructors registered by customizers still go to ruamel's shared classes"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vgrwbab3j2vxkn9q61r
created_at: 2026-10-25T07:51:56.860Z
updated_at: 2026-10-25T16:12:20.819Z
closed_at: 2026-10-25T16:12:20.819Z
close_reason: "fixed in 71e934a: each instance gets a private Constructor subclass too; tests cover constructors staying with the instance and every typ building."
resolution: null
duplicate_of: null
---
Low suggestion. src/frontmatter_format/yaml_util.py:80,101-102. Review A: https://github.com/jlevy/frontmatter-format/pull/8#pullrequestreview-5641789923. Give yaml.Constructor the same private subclass.
