---
type: is
id: is-01m5v5wgevpr3hss4b0mgn31s3
title: "C-first gate: admit only ruamel.yaml.clib's parser (a clibz CParser reporting libyaml 0.1.7 must stay pure); exclude ruamel.yaml 0.19.0"
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
created_at: 2026-10-26T04:00:51.163Z
updated_at: 2026-10-26T04:00:51.163Z
---
The build gate admits the C parser when the installed module reports libyaml 0.1.7 on ruamel.yaml 0.18-0.19. ruamel.yaml.clibz also reports 0.1.7 but is another build (Zig, free-threading flag) the differential search never covered. Patching ruamel.yaml.main.CParser to clibz's class (a stand-in for a future ruamel YAML() that imports clibz) made yaml_parser_mode() report c-first. Upstream changed loader priority in patch release 0.18.17, so this can happen within 0.19.x. Fix: admit only a CParser whose module is _ruamel_yaml or ruamel.yaml.clib._ruamel_yaml; tests for the clibz names and the real clib; exclude ruamel.yaml 0.19.0 (default clibz dependency, Zig build at install). Target: 0.5.1.
