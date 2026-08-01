---
title: Project Maintenance Playbook
description: Audited template, dependency, engineering, and release maintenance
category: planning
---
# Project Maintenance Playbook

Use this playbook for deliberate maintenance work.
Keep template adoption, dependency resolution, product fixes, and release publication
independently reviewable whenever their risk profiles differ.

## References

- [pyproject.toml](../../../pyproject.toml) — dependencies, build configuration, and
  tool settings
- [.copier-answers.yml](../../../.copier-answers.yml) — Simple Modern uv template
  version
- [Makefile](../../../Makefile) — frozen developer workflows
- [Development](../../development.md) — developer and supply-chain guidance
- [Publishing Releases](../../publishing.md) — release gates and publication process

## Update the Simple Modern uv Template

Start with a clean feature branch.
Preserve this project’s MIT license and public PyPI publishing choices explicitly so a
new template default cannot silently change them:

```shell
uvx copier@9.15.1 update --defaults --skip-answered \
  --data package_license=MIT \
  --data publish_to_pypi=true
```

Resolve all conflicts and inspect every generated change.
In particular, review build metadata, lock inputs, GitHub Actions SHAs and checksums,
the Makefile, and publishing instructions.
Confirm the selected template release and any package or action it changes are at least
14 days old unless an emergency exception is documented.

Template adoption does not authorize an unrestricted dependency upgrade.
During a release freeze, preserve existing dependency constraints and lock versions
unless a change is required for the template’s security model or meets the security
policy below.

## Review Dependency Changes

Classify each dependency as runtime, build, development, or CI before changing it.
Inspect open advisories and verify package names, maintainers, source repositories,
release dates, and artifact provenance.

- High or critical advisories block release in every dependency class until fixed or
  explicitly accepted after a documented audit.
- Every runtime advisory requires an explicit release decision.
- Low or medium advisories that affect only build, development, or CI tooling may be
  deferred when the affected behavior is not exercised by published artifacts.
- Do not take a release younger than the 14-day cooling-off period merely because it is
  newer. A security exception requires severity evidence and a supply-chain audit.

Upgrade only the reviewed package, then inspect the lock diff:

```shell
uv lock --no-config --exclude-newer "14 days" --upgrade-package package_name
UV_NO_CONFIG=1 UV_EXCLUDE_NEWER="14 days" \
  uv sync --all-extras --all-groups --frozen
git diff -- pyproject.toml uv.lock
```

An ordinary refresh outside a release freeze may use `make upgrade`, but still requires
the same audit and cooling-off checks.

## Run the Engineering Review

Load and apply the relevant tbd coding, Python, testing, documentation, and supply-chain
guidelines. Check the complete product surface for correctness, backward compatibility,
error handling, type safety, test gaps, dead code, and documentation drift.

Use check-only validation before committing:

```shell
uv sync --all-extras --all-groups --frozen
make lint-check
make test
```

## Validate Release Artifacts

Build from the reviewed lock graph without build isolation, validate both archives, and
install both into isolated environments:

```shell
export UV_NO_CONFIG=1
export UV_EXCLUDE_NEWER="14 days"
uv lock --check
release_dist_dir="$(mktemp -d)"
uv build --no-build-isolation --out-dir "${release_dist_dir}"
uv run --frozen python devtools/check_dist.py "${release_dist_dir}"

for artifact in "${release_dist_dir}"/*.whl "${release_dist_dir}"/*.tar.gz; do
  uv run --isolated --no-project --with "${artifact}" python -c \
    "import frontmatter_format"
done
```

The source distribution must contain only Hatch’s standard `.gitignore`, `LICENSE`,
`README.md`, `pyproject.toml`, `PKG-INFO`, and `src/frontmatter_format/**` beneath its
single archive root.
Internal agent state, issue data, workflows, hooks, tests, and arbitrary untracked files
are a release blocker.

## Land the Maintenance Work

Push the feature branch and open a PR with the exact validation commands and results.
Watch every CI job to completion, address review feedback, and merge only when required
checks are green and all release-blocking beads are closed.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
