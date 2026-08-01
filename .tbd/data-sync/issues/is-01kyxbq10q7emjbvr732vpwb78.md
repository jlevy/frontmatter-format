---
type: is
id: is-01kyxbq10q7emjbvr732vpwb78
title: "PR #3 review R1: restrict string parser to CR/LF newlines"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kyxbpq7zvywvnz0v2h76e2yv
created_at: 2026-08-01T00:31:19.062Z
updated_at: 2026-08-01T00:35:12.250Z
closed_at: 2026-08-01T00:35:12.243Z
close_reason: Fixed with a shared streaming parser backed by StringIO(newline="") and eight Unicode-separator regression cases.
---
PR #3 formal review R1. src/frontmatter_format/frontmatter_format.py:296. Replace splitlines behavior that treats Unicode separators as format newlines; add a regression test and preserve intended string offsets.
