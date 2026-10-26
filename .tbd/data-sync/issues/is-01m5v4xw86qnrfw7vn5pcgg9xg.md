---
type: is
id: is-01m5v4xw86qnrfw7vn5pcgg9xg
title: "Long documents with more than about 140 flow collections in all skip libyaml: _nesting_bound counts openers, not depth"
kind: feature
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:07.429Z
updated_at: 2026-10-26T03:44:07.429Z
---
`_nesting_bound` counts every `[` or `{` that can open a flow collection in the whole text, not the nesting depth, so a long record list with empty lists skips libyaml: a dump of 140 bead records each with `labels: []` has bound 153 > 150 and reads pure (130 records: 143, C-first). A 1,000-record, 600 KiB version reads at 0.78-0.92x of pure (two runs) (guard plus bound cost about 65 ms), against 4.5x for the same records without the empty lists. A tighter bound (for example a depth count that only overestimates) must still never undercount, or the C composer can overflow the C stack; it needs design, the small-stack subprocess tests and a fuzz rerun. Not a quick fix. Size M.
