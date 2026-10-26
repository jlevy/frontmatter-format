---
type: is
id: is-01m5v4xx7jbrsagpvr8sz71t13
title: Revisit ruamel.yaml.clibz only if a ruamel release's YAML() uses it (readers stay pure with it today)
kind: feature
status: open
priority: 4
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:08.433Z
updated_at: 2026-10-26T04:01:31.560Z
---
ruamel.yaml 0.19.1 lists ruamel.yaml.clib only under the oldlibyaml extra and ruamel.yaml.clibz>=0.3.7 under the libyaml extra; 0.19.0 depended on clibz by default. ruamel/yaml/main.py imports CParser only from _ruamel_yaml (clib), in every release through 0.19.1 and the upstream tip, and this library takes ruamel.yaml.main.CParser, so with clibz alone the readers are pure (verified 2026-10-26 in a scratch venv: ruamel.yaml[libyaml]==0.19.1, clibz 0.3.7, yaml_parser_mode() == 'pure'). Per the 2026-10-26 fact sheet: clibz bundles the same libyaml 0.1.7 sources as clib, is sdist-only (Zig build at install), and parsing to events took 107 ms vs clib's 105 ms, so there is no speed to gain. Revisit only if a ruamel release moves YAML() to clibz: then take its CParser, add the (ruamel, clibz) pair to the build gate and SEARCHED_PAIRS, and rerun the differential search. Related: the separate gate-hardening code PR (0.5.1) makes the gate fail closed on the parser's identity, so a clibz parser is reported as not a checked build.
