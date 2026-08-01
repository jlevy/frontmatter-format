# Publishing Releases

Frontmatter Format derives its version from Git tags.
Publishing a GitHub release with a stable `vMAJOR.MINOR.PATCH` tag is the only supported
trigger for the PyPI workflow.
The workflow checks out that exact tag, validates the version and artifacts, and uses
PyPI Trusted Publishing.
It has no manual dispatch path.

Publishing to PyPI cannot be undone or replaced with different files under the same
version. Complete every gate below before creating the GitHub release.

## One-Time Trusted Publisher Setup

The PyPI project must authorize `jlevy/frontmatter-format` and
`.github/workflows/publish.yml` as a trusted publisher.
Configure that relationship in
[PyPI’s publishing settings](https://pypi.org/manage/account/publishing/) and leave the
environment name blank unless the workflow is updated to use a protected environment.

## Prepare the Release Commit

Work from an up-to-date, clean `main` and record the exact commit that will be tagged:

```shell
git switch main
git pull --ff-only origin main
git status --short

release_sha="$(git rev-parse HEAD)"
test "${release_sha}" = "$(git rev-parse origin/main)"
```

Confirm the CI run for `release_sha` passed on every supported Python version.
Do not substitute an older green run:

```shell
gh run list --workflow=ci.yml --branch main --commit "${release_sha}" --limit 1
```

## Review Security and Supply-Chain State

Inspect all open Dependabot alerts and classify each affected package as runtime, build,
development, or CI from `pyproject.toml`, `uv.lock`, and the built wheel metadata.

- High or critical advisories in any class block publication.
- Every runtime advisory needs an explicit release decision.
- Low or medium alerts confined to non-runtime tooling may be deferred with a recorded
  rationale when the vulnerable behavior cannot affect the released artifacts.
- Dependency releases younger than 14 days remain excluded.
  A serious security update may bypass the cooling-off period only after its source,
  maintainers, release history, and published artifacts have been audited and the
  exception is recorded.

Inspect the alerts with:

```shell
gh api repos/jlevy/frontmatter-format/dependabot/alerts --paginate
```

Also verify that workflow actions remain pinned to reviewed full commit SHAs and that
the uv version and checksum are still paired.
Repository or organization settings that permit unpinned actions should be recorded as
defense-in-depth follow-up; workflow SHA pins remain mandatory.

## Run the Frozen Validation Gate

Install exactly the reviewed lock graph, run check-only linting, and run the complete
test suite:

```shell
export UV_NO_CONFIG=1
export UV_EXCLUDE_NEWER="14 days"
uv lock --check
uv sync --all-extras --all-groups --frozen
make lint-check
make test
```

Build both artifacts without an isolated, newly resolved build environment.
Use a new temporary output directory so stale artifacts cannot satisfy the checks:

```shell
release_dist_dir="$(mktemp -d)"
uv build --no-build-isolation --out-dir "${release_dist_dir}"
uv run --frozen python devtools/check_dist.py "${release_dist_dir}"
```

The validator requires exactly one wheel and one source distribution, matching package
versions, safe archive paths, and a minimal source payload.
It rejects repository automation, `.tbd`, agent integrations, tests, hooks, and
arbitrary untracked files.

Smoke-test installation from both artifacts:

```shell
for artifact in "${release_dist_dir}"/*.whl "${release_dist_dir}"/*.tar.gz; do
  uv run --isolated --no-project --with "${artifact}" python -c \
    "from importlib.metadata import version; import frontmatter_format; print(version('frontmatter-format'))"
done
```

## Prepare v0.4.0 Release Notes

Review the complete change set from the last release and verify that every user-visible
change is represented in [the v0.4.0 release notes](project/releases/v0.4.0.md):

```shell
git log v0.3.0.."${release_sha}" --oneline
git diff --stat v0.3.0.."${release_sha}"
```

Release notes use `## What's Changed`, grouped feature or fix sections, bold change
titles, and a concrete compare link.
Do not include template maintenance or internal cleanup unless it changes the user
experience or materially improves release safety.

## Publish v0.4.0

Reconfirm `release_sha`, the latest green CI run, and every blocking bead immediately
before publication. Then create the GitHub release at that exact commit:

```shell
gh release create v0.4.0 \
  --target "${release_sha}" \
  --title v0.4.0 \
  --notes-file docs/project/releases/v0.4.0.md
```

Do not create, move, or reuse the tag separately.
The release command creates it at the reviewed target, and the publish workflow verifies
that checkout is exactly tagged.

## Verify Publication

Watch the triggered workflow to its final state:

```shell
gh run list --workflow=publish.yml --event=release --limit 1
gh run watch RUN_ID --exit-status
```

After the workflow succeeds, verify the GitHub tag target, PyPI metadata, and an actual
install from PyPI:

```shell
test "$(git rev-list -n 1 v0.4.0)" = "${release_sha}"
uv run --isolated --no-project --with frontmatter-format==0.4.0 python -c \
  "from importlib.metadata import version; import frontmatter_format; assert version('frontmatter-format') == '0.4.0'"
```

Record the release URL, workflow URL, PyPI version, and smoke-test result in the release
bead. If the workflow fails before upload, fix the cause on a new commit and use a new
version; never move a published tag or attempt to replace PyPI files.

* * *

*This file was built with
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
