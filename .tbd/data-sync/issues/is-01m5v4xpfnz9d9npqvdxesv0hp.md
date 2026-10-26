---
type: is
id: is-01m5v4xpfnz9d9npqvdxesv0hp
title: Writer and reader bug fixes found in the v0.5.0 reconciliation
kind: epic
status: open
priority: 1
version: 10
labels: []
dependencies: []
child_order_hints:
  - is-01m5v4xpyzpnebafnr34e722kd
  - is-01m5v4xqfbacce5xnab5sv9d2c
  - is-01m5v4xr0qhfq8j8dnk4c6bsk0
  - is-01m5v4xrkh64gyjz6qwkz4yhfz
  - is-01m5v4xs2exjdmnwg6fd2c9dc1
  - is-01m5v4xsk6ynrqmg899a8s6q4a
  - is-01m5v6y3exhv9hhc50aaqr3z2x
  - is-01m5v6y3vq6dac3h8wjfntqvpk
  - is-01m5v9rz7kd6j7xyr9bmhj2d0e
created_at: 2026-10-26T03:44:01.525Z
updated_at: 2026-10-26T05:08:49.522Z
---
Bugs in the frontmatter writers and readers found while reconciling tracking after v0.5.0 (released at a9c3dc0, 2026-10-25). Each child has a reproduction run on main at a9c3dc0 (CPython 3.14, ruamel.yaml 0.19.1). None comes from #8 or #9; all predate 0.5.0.
