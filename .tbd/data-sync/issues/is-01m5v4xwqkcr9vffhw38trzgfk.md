---
type: is
id: is-01m5v4xwqkcr9vffhw38trzgfk
title: A default customizer that calls register_class turns C-first reading off for every read
kind: feature
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5v4xt44zmxeq19jrwnb3c3h
created_at: 2026-10-26T03:44:07.923Z
updated_at: 2026-10-26T03:44:07.923Z
---
`_accepts_c_parser` refuses any instance whose `_constructor` object exists, and ruamel's `register_class` builds it (`self.constructor.add_constructor`). So `add_default_yaml_customizer(lambda y: y.register_class(Point))` makes `yaml_parser_mode()` report "pure" and every read pure, including texts without the tag (verified at a9c3dc0). `add_default_yaml_representer` does not have this effect. Keeping C-first would need a check that the constructor object carries no state the C loader would drop; not a quick fix. Until then the README states it. Size M.
