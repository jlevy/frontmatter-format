---
type: is
id: is-01m5v4xsk6ynrqmg899a8s6q4a
title: fmf_has_frontmatter raises on an unterminated opening delimiter (a leading Markdown ---) instead of returning False
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:04.710Z
updated_at: 2026-10-26T04:36:49.403Z
closed_at: 2026-10-26T04:36:49.403Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head cc3e4ed, CI run 40268954420: all 12 jobs pass), commit cd5d831 (decision: return False). fmf_has_frontmatter now reads with strict=False and returns False for an opening delimiter with no closing one. fmf_read still raises on that input, as the README documents. Docstring updated. Detection is otherwise unchanged. Tests: test_fmf_has_frontmatter_detects_every_style (closed returns True and unclosed returns False, for all 6 styles), test_fmf_has_frontmatter_false_for_markdown_thematic_break, and test_fmf_has_frontmatter_other_cases (hash preamble, unclosed preamble, plain, empty and binary files). 8 cases failed on main.
resolution: null
duplicate_of: null
---
`fmf_has_frontmatter` is documented as "Returns True if the file has frontmatter, False otherwise", but it calls the strict reader, so a Markdown file that starts with a `---` thematic break and has no closing delimiter raises `FmFormatError: Delimiter --- for end of frontmatter not found` (reproduced at a9c3dc0).

Decide: read with strict=False there (returning False), or document the raise. `fmf_read` raising on the same file is intended (README: an opening delimiter without a closing one raises by default). Size S.
