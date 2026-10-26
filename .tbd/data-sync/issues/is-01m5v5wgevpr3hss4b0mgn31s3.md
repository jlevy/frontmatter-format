---
type: is
id: is-01m5v5wgevpr3hss4b0mgn31s3
title: "C-first gate: admit only ruamel.yaml.clib's parser (a clibz CParser reporting libyaml 0.1.7 must stay pure); exclude ruamel.yaml 0.19.0"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
created_at: 2026-10-26T04:00:51.163Z
updated_at: 2026-10-26T04:20:42.229Z
closed_at: 2026-10-26T04:20:42.229Z
close_reason: "Fixed in PR #14 (https://github.com/jlevy/frontmatter-format/pull/14), commit 57844ba (SSH-signed, GitHub verified). CHECKED_C_PARSER_MODULES admits only clib's parser; version read from the module holding that class. Evidence: real builds from branch source, CPython 3.13/ruamel.yaml 0.19.1: clib c-first, clib+clibz c-first, clibz-only pure, CParser patched to clibz pure (0.5.0: c-first). New tests fail 6x against 0.5.0's resolution, controls pass. ruamel-yaml>=0.18.10,!=0.19.0; lock only specifier changed. CI run 40268405413 all green (c-first/pure x 3.10-3.14, floor, lint); Qodo: 0 issues."
resolution: null
duplicate_of: null
---
The build gate admits the C parser when the installed module reports libyaml 0.1.7 on ruamel.yaml 0.18-0.19. ruamel.yaml.clibz also reports 0.1.7 but is another build (Zig, free-threading flag) the differential search never covered. Patching ruamel.yaml.main.CParser to clibz's class (a stand-in for a future ruamel YAML() that imports clibz) made yaml_parser_mode() report c-first. Upstream changed loader priority in patch release 0.18.17, so this can happen within 0.19.x. Fix: admit only a CParser whose module is _ruamel_yaml or ruamel.yaml.clib._ruamel_yaml; tests for the clibz names and the real clib; exclude ruamel.yaml 0.19.0 (default clibz dependency, Zig build at install). Target: 0.5.1.
