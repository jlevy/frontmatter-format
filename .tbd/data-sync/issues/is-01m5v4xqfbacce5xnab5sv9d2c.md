---
type: is
id: is-01m5v4xqfbacce5xnab5sv9d2c
title: "fmf_insert_frontmatter and fmf_strip_frontmatter drop the # preamble (shebang, PEP 723 block) before hash-style frontmatter"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xpfnz9d9npqvdxesv0hp
created_at: 2026-10-26T03:44:02.538Z
updated_at: 2026-10-26T04:36:48.027Z
closed_at: 2026-10-26T04:36:48.026Z
close_reason: |
  Fixed in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head cc3e4ed, CI run 40268954420: all 12 jobs pass), commit cd5d831. _rewrite_frontmatter copies the # lines that end at metadata_start_offset before the new frontmatter (insert) or before the body (strip). It takes the offsets from the same stream it copies from. Inserting a non-hash fm_style after those lines raises FmFormatError and leaves the file unchanged. Tests, all failing on main: test_fmf_insert_frontmatter_keeps_hash_preamble, test_fmf_strip_frontmatter_keeps_hash_preamble, test_insert_and_strip_keep_long_crlf_hash_preamble (a 400-line CRLF preamble with multi-byte characters), and test_fmf_insert_frontmatter_rejects_non_hash_style_after_hash_preamble (5 styles). The bead's repro now keeps "#!/usr/bin/env python\n# /// script\n# ///\n" after both insert and strip. The separate TODO for files with no frontmatter yet remains.
resolution: null
duplicate_of: null
---
For hash-style frontmatter preceded by `#` lines (a shebang or a PEP 723 `# /// script` block, which the format allows), `fmf_read_frontmatter_raw` returns `metadata_start_offset` > 0, but `fmf_insert_frontmatter` and `fmf_strip_frontmatter` copy the file from `content_offset` only, so those leading lines are lost.

Reproduction (a9c3dc0): file "#!/usr/bin/env python\n# /// script\n# ///\n#---\n# a: 1\n#---\nprint()\n": after `fmf_insert_frontmatter(p, {"b": 2}, fm_style=FmStyle.hash)` it is "#---\n# b: 2\n#---\nprint()\n"; after `fmf_strip_frontmatter(p)` it is "print()\n".

Fix: write `[0, metadata_start_offset)` of the original before the new frontmatter (insert) or before the body (strip). The existing TODO in `fmf_insert_frontmatter` (seek past `#` lines when the file has no frontmatter yet) is related but separate. Size S.
