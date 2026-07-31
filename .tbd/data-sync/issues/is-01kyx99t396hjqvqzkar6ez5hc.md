---
type: is
id: is-01kyx99t396hjqvqzkar6ez5hc
title: "PR #6 review R1: document round-trip alias write behavior"
kind: bug
status: closed
priority: 3
version: 3
labels: []
dependencies: []
parent_id: is-01kyx99fmt8e51ezeebewh2d3y
created_at: 2026-07-31T23:49:08.840Z
updated_at: 2026-07-31T23:50:13.394Z
closed_at: 2026-07-31T23:50:13.393Z
close_reason: "Fixed in reviewer commit 843351f and verified locally: README and regression coverage document rt alias expansion, and positional API calls are explicitly marked intentional."
---
R1 (Low), README.md:250: clarify that alias acceptance applies to reading only and test default expansion versus allow_aliases=True preservation. Reviewer reports this fixed in commit 843351f; verify and disposition.
