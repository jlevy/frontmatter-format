---
type: is
id: is-01m5v4xvmpy8ydabxc1vgq1jc6
title: fmf_read_raw opens the file twice; read the body from the same stream
kind: task
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:06.805Z
updated_at: 2026-10-26T03:44:06.805Z
---
`fmf_read_raw` (and so `fmf_read`) opens the file once in `fmf_read_frontmatter_raw` and again to read the body. Reading the body from the same stream (`seek(content_offset)`, then `read()`; on UnicodeDecodeError, `seek(0)` and `read()` raise as now) saves about 8 us per call (fmf_read_raw 26 us vs fmf_read_frontmatter_raw 18 us on a bead file) and closes the window where the file can change between the two opens. Size S. Safe: same values for a file that does not change during the call.
