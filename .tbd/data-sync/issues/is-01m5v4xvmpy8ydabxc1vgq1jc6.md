---
type: is
id: is-01m5v4xvmpy8ydabxc1vgq1jc6
title: fmf_read_raw opens the file twice; read the body from the same stream
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:06.805Z
updated_at: 2026-10-26T04:36:49.763Z
closed_at: 2026-10-26T04:36:49.763Z
close_reason: |
  Done in PR #15 https://github.com/jlevy/frontmatter-format/pull/15 (head cc3e4ed, CI run 40268954420: all 12 jobs pass), commit cd5d831. fmf_read_raw reads the frontmatter and the body from one open stream. For a non-UTF-8 file it seeks to 0, and the read raises UnicodeDecodeError as before. test_fmf_read_raw_opens_the_file_once failed on main, which opened the file twice. test_fmf_read_raw_results (8 cases), test_fmf_read_raw_raises_on_non_utf8 and test_fmf_read_raw_raises_on_unclosed_delimiter pin the results. Timing on a file with a 439-character frontmatter block, three interleaved runs: 22.3 to 24.3 us, against 27.6 to 40.5 us on main.
resolution: null
duplicate_of: null
---
`fmf_read_raw` (and so `fmf_read`) opens the file once in `fmf_read_frontmatter_raw` and again to read the body. Reading the body from the same stream (`seek(content_offset)`, then `read()`; on UnicodeDecodeError, `seek(0)` and `read()` raise as now) saves about 8 us per call (fmf_read_raw 26 us vs fmf_read_frontmatter_raw 18 us on a bead file) and closes the window where the file can change between the two opens. Size S. Safe: same values for a file that does not change during the call.
