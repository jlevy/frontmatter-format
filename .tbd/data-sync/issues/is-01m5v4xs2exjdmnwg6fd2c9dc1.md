---
type: is
id: is-01m5v4xs2exjdmnwg6fd2c9dc1
title: Blank, comment-only or ~ frontmatter raises FmFormatError while empty frontmatter reads as None
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:04.173Z
updated_at: 2026-10-26T03:44:04.173Z
---
`_parse_metadata` returns None for empty frontmatter (`---\n---\n`) but raises `FmFormatError: Expected YAML metadata to be a dict, got <class 'NoneType'>` when the YAML is a blank line, only comments, or `~` (`---\n\n---\n`, `---\n# note\n---\n`, `---\n~\n---\n`). All four read as "no metadata" in YAML.

Fix: return None when the parsed document is None; keep raising for other non-dict values. This changes a raise into None for those inputs; note it in the release notes. Size S.
