---
type: is
id: is-01m5v4xsk6ynrqmg899a8s6q4a
title: fmf_has_frontmatter raises on an unterminated opening delimiter (a leading Markdown ---) instead of returning False
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:04.710Z
updated_at: 2026-10-26T03:44:04.710Z
---
`fmf_has_frontmatter` is documented as "Returns True if the file has frontmatter, False otherwise", but it calls the strict reader, so a Markdown file that starts with a `---` thematic break and has no closing delimiter raises `FmFormatError: Delimiter --- for end of frontmatter not found` (reproduced at a9c3dc0).

Decide: read with strict=False there (returning False), or document the raise. `fmf_read` raising on the same file is intended (README: an opening delimiter without a closing one raises by default). Size S.
