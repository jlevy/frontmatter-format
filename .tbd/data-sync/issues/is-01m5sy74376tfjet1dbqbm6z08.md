---
type: is
id: is-01m5sy74376tfjet1dbqbm6z08
title: Ask tbd upstream to let setup write the agents-md block through a symlinked AGENTS.md (or report it skipped, not failed); until then the block in docs/development.md is hand-copied
kind: task
status: open
priority: 3
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T16:27:35.910Z
updated_at: 2026-10-26T03:42:40.605Z
---
Verified 2026-10-26 with tbd v0.10.0 in a scratch clone: `tbd setup --auto --surfaces=agents-md` prints 'Refusing to update .../AGENTS.md: expected a regular file, but found a symbolic link' and 'Error: Setup failed for 1 selected integration surface', and exits 1. AGENTS.md and CLAUDE.md are symlinks to docs/development.md, whose agents-md block (between the BEGIN/END TBD INTEGRATION markers) is copied by hand on each tbd upgrade, as the comment above it says. The ask for jlevy/tbd: write the block through a symlink that resolves inside the repository, or report the surface as skipped rather than failed. No jlevy/tbd issue covers this yet (issue search for 'symlink', 2026-10-26); filing one is the remaining step.
