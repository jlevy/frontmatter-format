---
type: is
id: is-01m5tbtvc0hnx3rr4znb5kdgrj
title: "PR #9 F1: 200-level bound has no margin on 64 KB threads; docstring stack assumption"
kind: bug
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m5tbttq3rn0kv50q0qp3a24d
created_at: 2026-10-25T20:25:33.824Z
updated_at: 2026-10-25T20:33:11.024Z
closed_at: 2026-10-25T20:33:11.024Z
close_reason: "fixed in ff31427: _C_SCAN_DEPTH=150; docstring records the 64 KB measurements (165-201 on 3.10-3.13; 3.14 clean RecursionError at 74), the stack assumption and the cost; tests follow the constant."
resolution: null
duplicate_of: null
---
Low. Review F. Lower _C_SCAN_DEPTH to 150; document 64 KB measurements (165/192/201/201 on 3.10-3.13; 3.14 clean RecursionError at 74).
