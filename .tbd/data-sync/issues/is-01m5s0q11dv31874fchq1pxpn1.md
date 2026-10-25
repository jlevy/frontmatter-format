---
type: is
id: is-01m5s0q11dv31874fchq1pxpn1
title: "PR #9 B7: bytes/stream inputs fail only when the extension is installed"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T07:51:59.789Z
updated_at: 2026-10-25T16:12:23.023Z
closed_at: 2026-10-25T16:12:23.023Z
close_reason: "fixed in 5c03725: _load_yaml_text takes the C path only for str; bytes and streams go to pure ruamel; tests with and without the extension."
resolution: null
duplicate_of: null
---
Medium. src/frontmatter_format/yaml_util.py:206; _libyaml_guard.py:133-135. Review B: https://github.com/jlevy/frontmatter-format/pull/9#pullrequestreview-5642097227. C path only for str.
