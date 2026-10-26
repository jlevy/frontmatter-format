---
type: is
id: is-01m5v4xtjz5jv382d4jhzjh7t5
title: "_nesting_bound: write its three regexes literal-first (same matches; 29 to 8 us typical, 58 to 13 ms on 600 KiB)"
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:05.727Z
updated_at: 2026-10-26T04:20:42.563Z
closed_at: 2026-10-26T04:20:42.562Z
close_reason: "Done in PR #14 (https://github.com/jlevy/frontmatter-format/pull/14), commit b550357 (SSH-signed, GitHub verified). Literal-first _nesting_bound regexes; _c_eligible uses _nests_within (count shortcut, exact fallback). Rerun differential on 400,182 texts (repo + bead corpus, 200k generator, 200k random): 0 term/bound mismatches, 0 _nests_within mismatches at 10 limits, 0 _c_eligible mismatches. Typical 439 chars: 27.3 us -> 7.4 us (regex) -> 1.08 us (shortcut); 598 KiB: 46.6 -> 12.2/13.0 ms; 76/76 bead files take the shortcut. Tests: same match spans, same decision on both branches and the shortcut edge. CI run 40268405413 green; Qodo: 0 issues."
resolution: null
duplicate_of: null
---
`_FLOW_OPEN` (`(?<![^ \t\r\n\[{,:?])[\[{]`) and `_LINE_INDENT` (`(?<![^\r\n]) +`) start with a lookbehind, so the regex engine tries every position; `_INDICATOR_CHAIN` (`(?:[-?] +)+`) starts with a group. Writing them literal-first, as the guards in `_libyaml_guard` already do: `[\[{](?<![^ \t\r\n\[{,:?][\[{])`, ` (?<![^\r\n] ) *`, `[-?] +(?:[-?] +)*`.

Measured (prototype): `_nesting_bound` 29 -> 8 us on a 439-character block, 58 -> 13 ms on a 600 KiB document whose C-first read is about 250 ms. Identical results on 400,286 texts (repo and bead corpus, 200,000 fuzz-generator texts, 200,000 random texts over " \n\r-?[{,:\t\x85ab"). Add that differential as a test. Size S. Safe: same counts, so the same routing.
