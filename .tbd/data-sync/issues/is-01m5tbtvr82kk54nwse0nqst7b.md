---
type: is
id: is-01m5tbtvr82kk54nwse0nqst7b
title: "PR #9 F2: small-stack tests skip on an observed segfault instead of the Python version"
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5tbttq3rn0kv50q0qp3a24d
created_at: 2026-10-25T20:25:34.215Z
updated_at: 2026-10-25T20:33:11.370Z
closed_at: 2026-10-25T20:33:11.369Z
close_reason: "fixed in ff31427: skips conditioned on a runtime Python 3.10 check with the reason named; non-zero exit asserted there, failure elsewhere."
resolution: null
duplicate_of: null
---
Low. Review F. Condition on sys.version_info < (3, 11); assert the exit code there.
