---
type: is
id: is-01m5v4xtjz5jv382d4jhzjh7t5
title: "_nesting_bound: write its three regexes literal-first (same matches; 29 to 8 us typical, 58 to 13 ms on 600 KiB)"
kind: task
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:05.727Z
updated_at: 2026-10-26T03:44:05.727Z
---
`_FLOW_OPEN` (`(?<![^ \t\r\n\[{,:?])[\[{]`) and `_LINE_INDENT` (`(?<![^\r\n]) +`) start with a lookbehind, so the regex engine tries every position; `_INDICATOR_CHAIN` (`(?:[-?] +)+`) starts with a group. Writing them literal-first, as the guards in `_libyaml_guard` already do: `[\[{](?<![^ \t\r\n\[{,:?][\[{])`, ` (?<![^\r\n] ) *`, `[-?] +(?:[-?] +)*`.

Measured (prototype): `_nesting_bound` 29 -> 8 us on a 439-character block, 58 -> 13 ms on a 600 KiB document whose C-first read is about 250 ms. Identical results on 400,286 texts (repo and bead corpus, 200,000 fuzz-generator texts, 200,000 random texts over " \n\r-?[{,:\t\x85ab"). Add that differential as a test. Size S. Safe: same counts, so the same routing.
