---
title: Project Maintenance Playbook
description: Full project maintenance including template upgrade, dependency upgrades, engineering review, and PR
category: planning
---
Comprehensive project maintenance playbook. Run all steps in order.

## References

- [pyproject.toml](../../../pyproject.toml) — deps, build config, tool settings
- [.copier-answers.yml](../../../.copier-answers.yml) — template version tracking
- [Makefile](../../../Makefile) — dev workflow shortcuts
- [docs/development.md](../../development.md) — dev setup and workflows

## 1. Upgrade Copier Template

```bash
copier update --defaults --trust
```

- Check `.copier-answers.yml` for the new template version.
- Resolve all merge conflicts. Preserve project-specific customizations
  (e.g. `requires-python`, CI matrix versions, license year ranges).
- Review all changed files: CI workflows, pyproject.toml, Makefile, docs.
- Commit the template upgrade separately.

## 2. Upgrade All Dependencies

```bash
uv sync --upgrade --all-extras
```

- Verify lint and tests pass after upgrade: `make lint` and `make test`.
- Commit the updated `uv.lock` separately.

## 3. Engineering Review

Load and apply relevant guidelines:

```bash
tbd guidelines general-coding-rules
tbd guidelines general-comment-rules
tbd guidelines python-rules
tbd guidelines python-modern-guidelines
tbd guidelines error-handling-rules
tbd guidelines general-testing-rules
```

Review the full codebase against these guidelines. Check for:

- Missing functionality or broken entry points
- Incomplete feature coverage (e.g. write paths that lack matching read paths)
- Type annotation gaps
- Test coverage gaps
- Security issues

Fix all issues found. Run `make lint` and `make test` after each fix.
Commit fixes separately with descriptive messages.

## 4. Final Verification

```bash
make   # runs install, lint, test
```

Confirm zero lint errors, zero test failures.

## 5. Push and PR

- Push to feature branch.
- Create PR with summary of all changes.
- Monitor CI: `gh pr checks <PR> --watch`
- Wait for CI to pass on all Python versions in the matrix.
- Address any review comments, balancing fix quality against issue severity.
