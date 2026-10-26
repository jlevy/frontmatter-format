---
type: is
id: is-01m5v4xs2exjdmnwg6fd2c9dc1
title: Blank, comment-only or ~ frontmatter raises FmFormatError while empty frontmatter reads as None
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:04.173Z
updated_at: 2026-10-26T04:36:49.066Z
closed_at: 2026-10-26T04:36:49.066Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head cc3e4ed, CI run 40268954420: all 12 jobs pass), commit cd5d831. _parse_metadata returns None when the YAML parses to None, and still raises FmFormatError for other non-mapping values. Documented in the fmf_read and fmf_read_frontmatter docstrings. The release-note text is in the PR #15 body, for the separate notes PR. Tests: test_blank_comment_or_null_frontmatter_reads_as_none (blank, whitespace, comment, ~, null, hash-style comment and ~; 7 failed on main) and test_non_dict_non_null_metadata_still_raises (list, string, int, bool, empty string).
resolution: null
duplicate_of: null
---
`_parse_metadata` returns None for empty frontmatter (`---\n---\n`) but raises `FmFormatError: Expected YAML metadata to be a dict, got <class 'NoneType'>` when the YAML is a blank line, only comments, or `~` (`---\n\n---\n`, `---\n# note\n---\n`, `---\n~\n---\n`). All four read as "no metadata" in YAML.

Fix: return None when the parsed document is None; keep raising for other non-dict values. This changes a raise into None for those inputs; note it in the release notes. Size S.
