---
type: is
id: is-01m5v4xx7jbrsagpvr8sz71t13
title: Readers stay pure with ruamel.yaml.clibz (ruamel.yaml 0.19's libyaml extra)
kind: feature
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:08.433Z
updated_at: 2026-10-26T03:44:08.433Z
---
ruamel.yaml 0.19.1 lists `ruamel.yaml.clib` only under the `oldlibyaml` extra and adds `ruamel.yaml.clibz>=0.3.7` under the `libyaml` extra. `ruamel/yaml/main.py` imports `CParser` only from `_ruamel_yaml` (clib), and this library takes `ruamel.yaml.main.CParser`, so with clibz alone the readers are pure (verified in a scratch venv: `ruamel.yaml[libyaml]==0.19.1`, clibz 0.3.7, `yaml_parser_mode()` == "pure"). clibz reports libyaml 0.1.7 too. Supporting it would mean taking clibz's CParser, checking that ruamel's C load path accepts it, adding the (ruamel, clibz) pair to the build gate and `SEARCHED_PAIRS`, and rerunning the differential search on it. Size M.
