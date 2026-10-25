---
type: is
id: is-01m5t1aq2azyhmabnkjafxv8d0
title: "PR #9 D1: commit 75b40dc message names the private downstream repository"
kind: bug
status: closed
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01m5t1apgk247f0502qqasce3m
created_at: 2026-10-25T17:21:59.370Z
updated_at: 2026-10-25T20:39:18.186Z
closed_at: 2026-10-25T20:39:18.186Z
close_reason: "Squash-merged #9 as 5853079 with an explicit clean subject/body (stack unstacked first); no private names in main history since v0.4.0; commit verified."
resolution: null
duplicate_of: null
---
High. Review D. Disposition: fixed at merge. The coordinator merges #8 alone, syncs, then squash-merges #9 with an explicit clean subject/body (gh pr merge --squash --subject --body-file); see fmf-416u. Owner also deletes the first PR-body revision by hand (no API). No history rewrite on the branch.
