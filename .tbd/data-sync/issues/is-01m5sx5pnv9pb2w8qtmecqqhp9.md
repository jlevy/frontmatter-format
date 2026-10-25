---
type: is
id: is-01m5sx5pnv9pb2w8qtmecqqhp9
title: "PR #9 Qodo 4370103219: deep tagged YAML bypasses the depth check via a non-container constructor"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rt1vxfr5386jbaef1gyq4r
created_at: 2026-10-25T16:09:20.826Z
updated_at: 2026-10-25T16:12:25.416Z
closed_at: 2026-10-25T16:12:25.416Z
close_reason: "fixed in a3ba9ca: the C attempt wraps the instance's Constructor so construct_document checks depth and sharing on the composed nodes before construction; a 600-deep !box document raises RecursionError as pure ruamel does, and the check runs before any constructor; tests test_a_tag_constructor_cannot_hide_depth_from_the_c_check, test_the_depth_check_runs_before_construction, test_node_walk_counts_depth_and_shared_nodes."
resolution: null
duplicate_of: null
---
Medium (Qodo). src/frontmatter_format/yaml_util.py (depth check on the constructed value). Inline comment: https://github.com/jlevy/frontmatter-format/pull/9#discussion_r4370103219. Found by the discovery sweep while addressing review B; outside the brief's letters. Fix: check depth and sharing on the nodes libyaml composed, before construction.
