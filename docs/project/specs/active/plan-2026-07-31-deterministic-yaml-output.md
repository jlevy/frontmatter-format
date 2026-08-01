# Feature: Deterministic, Alias-Free YAML Output

**Date:** 2026-07-31 (last updated 2026-07-31)

**Author:** Joshua Levy and Codex

**Status:** Implemented

## Overview

Make YAML emitted from Python metadata independent of Python object identity. Equal
acyclic values should serialize identically whether callers construct them from fresh
containers or reuse the same container instance. Frontmatter written from mappings
will therefore avoid YAML anchors and aliases by default.

The change will also replace the opaque recursion failure for cyclic values with an
explicit serialization error and retain an opt-in for callers that deliberately need
full YAML graph semantics. YAML timestamp behavior remains unchanged and will be
documented as a portability tradeoff.

## Goals

- Emit identical YAML for equal acyclic values regardless of shared Python container
  identity
- Keep mapping-based `fmf_write` output free of automatically generated anchors and
  aliases
- Fail clearly on cyclic values when aliases are disabled
- Preserve the current alias and cycle behavior through an explicit low-level opt-in
- Preserve `date` and `datetime` YAML timestamp round-tripping
- Explain how callers can maximize cross-language portability

## Non-Goals

- Define or enforce a JSON-compatible subset of YAML
- Reject aliases, anchors, or timestamps while reading YAML
- Change raw YAML strings supplied to `fmf_write`
- Convert Python `date` or `datetime` values to strings automatically
- Guarantee canonical output for differences other than shared object identity

## Background

GitHub issue #4 reports that ruamel.yaml emits anchors and aliases when the same Python
container instance appears in more than one place. Equal mappings can consequently
produce different bytes solely because of how the caller constructed the object graph.
This makes output surprising, less portable across YAML implementations, and unstable
for diffs and content hashes.

Setting the representer's `ignore_aliases` policy removes anchors for repeated acyclic
objects under both the round-trip and safe representers. Doing that alone causes a
cyclic object graph to recurse until Python raises `RecursionError`, so cycle handling
must be part of the change.

The issue also asks whether Python dates should be emitted as YAML timestamps. That
behavior is deliberate: it preserves the Python type when the library reads its own
output. A true portable-value mode would need to cover the complete JSON-compatible
value domain, not only timestamps and aliases. The softschema portable YAML rules, for
example, also constrain mapping keys, duplicate keys, merge keys, explicit tags,
numbers, Unicode, size, and nesting.

## Design

### Approach

Add an `allow_aliases` output option that defaults to `False`. When aliases are not
allowed, the configured representer will duplicate repeated acyclic values and track
the identities on the active representation path. Encountering an identity already on
that active path indicates a genuine cycle and raises `YamlSerializationError` with an
actionable message. Encountering the same identity after its earlier representation has
finished is ordinary sharing and remains valid.

The active-path state must be cleared in `finally` blocks as representation unwinds.
The guard belongs in the configured representer, not only in convenience wrappers, so
direct `new_yaml().dump(...)` calls receive the same behavior.

`allow_aliases=True` leaves ruamel.yaml's normal alias behavior intact. This is an
explicit escape hatch for low-level YAML utility callers and supports cyclic graphs.
`fmf_write` will not expose the option: mapping-based frontmatter uses the alias-free
default. Callers can still provide an intentionally authored raw YAML string.

Readers remain permissive. `from_yaml_string`, `read_yaml_file`, and frontmatter read
functions will continue to accept aliases and timestamps supported by ruamel.yaml.

### Components

- `src/frontmatter_format/yaml_util.py`
  - Define `YamlSerializationError`
  - Configure alias policy and active-path cycle detection in `new_yaml`
  - Propagate `allow_aliases` through YAML output helpers
- `src/frontmatter_format/__init__.py`
  - Export the serialization error with the other public helpers
- `src/frontmatter_format/frontmatter_format.py`
  - Continue using the alias-free default for mapping metadata
- `tests/test_yaml_util.py`
  - Cover identity-independent output, cycles, opt-in aliases, and timestamps
- `tests/test_frontmatter_format.py`
  - Verify mapping-based frontmatter output contains no generated aliases
- `README.md`
  - Document writer behavior and timestamp portability guidance

### API Changes

Append `allow_aliases: bool = False` to these signatures so existing positional calls
remain compatible:

- `new_yaml`
- `to_yaml_string`
- `dump_yaml`
- `write_yaml_file`

Add public `YamlSerializationError`, derived from the existing YAML representation error
type so callers already catching ruamel.yaml representation failures continue to work.

Do not add `allow_aliases` to `fmf_write`. Raw string metadata remains an explicit way
to write full YAML without transformation.

### Backward Compatibility

- **Code types, methods, and function signatures: SUPPORT BOTH.** Existing calls keep
  their signatures and require no migration; the new option is appended with a default.
- **Library APIs: SUPPORT BOTH.** Alias-free output becomes the default, while
  `allow_aliases=True` preserves the previous low-level writer behavior for shared and
  cyclic object graphs.
- **Server APIs: N/A.** The project exposes no server interface.
- **File formats: SUPPORT BOTH.** New mapping-based writes avoid generated aliases, but
  readers continue accepting existing YAML files with aliases and timestamps. Raw YAML
  string writes remain unchanged.
- **Database schemas: N/A.** The project has no database schema.

## Implementation Plan

### Phase 1: Alias-Free Writing and Documentation

- [x] Add failing tests for shared dictionaries and lists under `typ="rt"` and
  `typ="safe"`
- [x] Add failing tests for cycle errors and `allow_aliases=True`
- [x] Add timestamp and date-looking string regression tests
- [x] Implement the representer alias policy, active-path guard, error type, and output
  helper parameters
- [x] Add frontmatter writer coverage for shared mapping metadata
- [x] Document alias behavior, cycle behavior, and timestamp portability
- [x] Change the introductory timestamp example to a quoted ISO string
- [x] Run formatting, linting, type checking, and the complete test suite

## Testing Strategy

- Compare the complete output of equal shared and unshared structures, rather than only
  checking for anchor characters
- Parameterize core serialization cases over the safe and round-trip representers
- Cover shared dictionaries and lists so both mapping and sequence representation paths
  are exercised
- Verify a self-referential container raises `YamlSerializationError` by default
- Verify `allow_aliases=True` emits an anchor and alias and can represent the cycle
- Verify `date` and `datetime` values still deserialize to their original Python types
- Verify ISO date-looking strings are quoted and deserialize as strings
- Verify `fmf_write` produces alias-free frontmatter and leaves raw YAML strings alone
- Run `make` for the repository's full validation suite

Validation completed on 2026-07-31. `make` passed with zero lint or type-check warnings
and all 21 tests passed independently on every supported Python version from 3.10
through 3.14.

## Rollout Plan

Ship the change in the next normal release and call out the output behavior change in
the release notes. Repeated shared values may produce larger output because they are
expanded rather than deduplicated. Low-level callers that depend on anchors or cyclic
graphs can restore the prior behavior with `allow_aliases=True`.

No migration is needed for existing files. Readers remain compatible with files that
already contain aliases or timestamps.

## Open Questions

None. A comprehensive portable-value mode requires a separate specification before
implementation.

## References

- [GitHub issue #4](https://github.com/jlevy/frontmatter-format/issues/4)
- [softschema portable YAML values](https://github.com/jlevy/softschema/blob/main/docs/softschema-spec.md#portable-yaml-values)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
