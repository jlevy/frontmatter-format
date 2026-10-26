---
type: is
id: is-01m5v5n08jhvkjqw8ard2p3rnr
title: "PR #13: replace the README clib install placeholder with the verified paragraph before merge"
kind: task
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-26T03:56:45.201Z
updated_at: 2026-10-26T03:56:45.201Z
---
PR https://github.com/jlevy/frontmatter-format/pull/13 (branch claude/specs-status-0.5.0) adds the README Performance and Custom YAML Types sections for 0.5.0. Its Performance section holds an HTML comment 'PLACEHOLDER: how to install ruamel.yaml.clib' where the install paragraph goes. The coordinator is sending verified wording. Background: ruamel.yaml 0.19.1 lists ruamel.yaml.clib only under the oldlibyaml extra, and its libyaml extra installs ruamel.yaml.clibz, which YAML() and these readers do not use (see fmf-lzs0). Replace the comment, rerun flowmark --auto and make lint-check, push, and get CI green. Merge is the owner's call.
