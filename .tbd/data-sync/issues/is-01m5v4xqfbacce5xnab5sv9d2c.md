---
type: is
id: is-01m5v4xqfbacce5xnab5sv9d2c
title: "fmf_insert_frontmatter and fmf_strip_frontmatter drop the # preamble (shebang, PEP 723 block) before hash-style frontmatter"
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:02.538Z
updated_at: 2026-10-26T03:44:02.538Z
---
For hash-style frontmatter preceded by `#` lines (a shebang or a PEP 723 `# /// script` block, which the format allows), `fmf_read_frontmatter_raw` returns `metadata_start_offset` > 0, but `fmf_insert_frontmatter` and `fmf_strip_frontmatter` copy the file from `content_offset` only, so those leading lines are lost.

Reproduction (a9c3dc0): file "#!/usr/bin/env python\n# /// script\n# ///\n#---\n# a: 1\n#---\nprint()\n": after `fmf_insert_frontmatter(p, {"b": 2}, fm_style=FmStyle.hash)` it is "#---\n# b: 2\n#---\nprint()\n"; after `fmf_strip_frontmatter(p)` it is "print()\n".

Fix: write `[0, metadata_start_offset)` of the original before the new frontmatter (insert) or before the body (strip). The existing TODO in `fmf_insert_frontmatter` (seek past `#` lines when the file has no frontmatter yet) is related but separate. Size S.
