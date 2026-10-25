---
type: is
id: is-01m5s0q29q16bjbwyv90ptv8jh
title: "PR #9 B10: guard implemented twice (here and softschema #62) and the copies drifted"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:52:01.078Z
updated_at: 2026-10-25T16:12:23.851Z
closed_at: 2026-10-25T16:12:23.851Z
close_reason: "fixed (option 2): B1, B3 and B6 are in both copies (softschema already had B1/B6; B3 does not apply to its loader), the module docstring documents which families are shared and why each repo has the others, and the search script is committed as devtools/yaml_parser_fuzz.py. Reviewer's cross.py: 179 fixtures of both repos read identically C-first and pure in both packages. A single owner (export the guard as public API) is not taken in this PR: it is a public-API design decision and a release dependency for softschema."
resolution: null
duplicate_of: null
---
Medium, alignment. src/frontmatter_format/_libyaml_guard.py vs softschema _portable.py. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. Align families and gate; document divergences; commit the search script.
