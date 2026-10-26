---
type: is
id: is-01m5v4xy95kkr5rwc8k0g89bmt
title: "Delete PR #9's original body revision from GitHub's edit history (owner, UI only)"
kind: task
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-26T03:44:09.509Z
updated_at: 2026-10-26T03:44:09.509Z
---
fmf-1oqz rewrote PR #9's body without the private downstream references and noted that the earlier revision in GitHub's edit history must be deleted by hand (there is no API for it). Checked 2026-10-26 with the GraphQL `userContentEdits` of PR #9: 4 revisions, none deleted, and the original body (edited 2026-10-25T01:46:13Z) still contains the downstream references the rewrite removed. Owner action in the GitHub UI: PR #9 header, "edited" menu, open that revision, "Delete revision". Close with the `userContentEdits` check showing it deleted.
