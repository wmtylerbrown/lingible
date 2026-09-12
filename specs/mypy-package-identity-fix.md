---
id: SPEC-INFRA-MYPY-001
title: Resolve the src package/mypy_path module-identity ambiguity at its root
status: approved
approval: autonomous
confidence: medium
risk: low
capability: "Infrastructure & deployment (CDK: Shared/Data/Async/Api/Website stacks)"
issue: 13
security_review: false
security_domains: []
cost_review: false
affected_docs: []
derived_decisions: 2
implementation_decisions: 2
escalated_decisions: 0
security_test_ref: null
---

# Resolve the src package/mypy_path module-identity ambiguity at its root

## Intent

`.github/workflows/verify.yml` and `scripts/verify` both invoke
`poetry run mypy --explicit-package-bases src/` in `backend/lambda`. The flag is a workaround
(added while landing the CI pipeline in #11) for a latent ambiguity: `backend/lambda/mypy.ini` sets
`mypy_path = src` (so bare imports like `from models.user import User` resolve, matching the
`PYTHONPATH=backend/lambda/src` convention in `AGENTS.md`), and `backend/lambda/src/__init__.py`
makes `src` itself an importable package. Combined, every file under `src/` is reachable under two
different fully-qualified module names (`src.models.x` via the `__init__.py` chain, `models.x` via
`mypy_path`), and a plain `mypy src/` fails with "Source file found twice under different module
names" on every run, independent of which files changed.

Separately, `.pre-commit-config.yaml`'s mypy hook runs per-changed-file from the repo root and
never loads `backend/lambda/mypy.ini` — it has been running with only `--ignore-missing-imports`,
without the pydantic plugin or the per-module `ignore_missing_imports` overrides that `mypy.ini`
declares. Local pre-commit checks pass a materially weaker type check than `scripts/verify`/CI run,
which can let real mypy findings reach a PR undetected by pre-commit.

This spec covers removing the root cause of the ambiguity (so `--explicit-package-bases` is no
longer needed as a workaround) and making the pre-commit mypy hook use the project's actual mypy
configuration, so local and CI type-checking agree.

This spec does not cover any change to the type-checking rules themselves (strictness, per-module
overrides) — only how mypy resolves module identity and which config it reads.

## Existing decisions

- `AGENTS.md` (Python Path): `PYTHONPATH=backend/lambda/src` is the project convention for local
  development and test runs; code imports modules bare (`from models.user import User`), never
  with a `src.` prefix.
- `backend/lambda/pyproject.toml`: `packages = [{include = "src"}]` under `[tool.poetry]`. No
  script in the repository runs `poetry build`; `poetry install` (CI and local setup) and
  `poetry export` (Lambda dependency bundling, `backend/cdk/scripts/build-lambda-packages.js`) are
  the only Poetry commands used against this project.
- `backend/cdk/scripts/build-lambda-packages.js`: copies the contents of `backend/lambda/src/`
  directly into each Lambda artifact's root and relies on the Lambda runtime adding that directory
  to `sys.path` — it does not import anything as `src.*` or depend on `src` being a Python package.
- `backend/lambda/mypy.ini`: the canonical mypy configuration (pydantic plugin,
  `ignore_missing_imports` overrides for `boto3`, `pydantic`, `googleapiclient`, etc.,
  `mypy_path = src`). `scripts/verify` and CI already read it (via `poetry run mypy`, invoked from
  `backend/lambda`); `.pre-commit-config.yaml` does not.

## Behavior

- Running `mypy src/` (or the equivalent invocation used by `scripts/verify`/CI) from
  `backend/lambda` succeeds without reporting "Source file found twice under different module
  names" for any file under `src/`, using the mypy invocation as it exists after this change
  (whether or not `--explicit-package-bases` is still present — see Agent decisions).
- `poetry install` and `poetry export` (both invoked exactly as they are today, from
  `backend/lambda`) continue to succeed and produce the same dependency set as before this change.
- `backend/cdk/scripts/build-lambda-packages.js` continues to produce Lambda artifacts with the
  same file layout and import behavior as before this change (bare imports of `handlers.*`,
  `models.*`, etc. from the artifact root, unaffected by anything under `backend/lambda/src`'s
  package structure).
- The pre-commit mypy hook (`.pre-commit-config.yaml`), run against a file under
  `backend/lambda/src/`, applies the same configuration as `scripts/verify`'s mypy invocation:
  the pydantic mypy plugin is active, and the per-module `ignore_missing_imports` overrides in
  `backend/lambda/mypy.ini` apply. A file that would produce a given mypy diagnostic under
  `scripts/verify` must produce the same diagnostic (not a spurious import-resolution error, and
  not a false negative from the plugin being inactive) under the pre-commit hook.
- No behavior of any Lambda handler, any test, or any deployed artifact changes as a result of this
  spec. This is a build/type-checking-tooling-only change.

## Actors and authorization

None — this is development tooling with no runtime actor, request, or authorization surface.

## Privacy and data classification

None. No PII or persisted data is read or written by this change.

## Cost impact

None.

## Acceptance criteria

1. From `backend/lambda`, the project's mypy invocation (as used by `scripts/verify` and CI) exits
   0 against the current `src/` tree, and does so whether the mypy invocation still carries
   `--explicit-package-bases` or has had it removed.
2. `scripts/verify` passes end to end (mypy, tests, and the existing Bedrock-cost-review check all
   still run and pass).
3. `poetry install` and `poetry export --format=requirements.txt` (or the exact `poetry export`
   invocation `build-lambda-packages.js` uses) both succeed, producing dependency output equivalent
   to before this change (no missing or renamed packages).
4. `backend/cdk/scripts/build-lambda-packages.js` (or its equivalent test/dry-run) still produces
   Lambda artifacts whose handler entry points import successfully — i.e. the packaging change does
   not alter what ends up in the artifact under `src/`'s former contents.
5. Running the pre-commit mypy hook against a `backend/lambda/src/*.py` file that currently exists
   only because it satisfies the pydantic plugin (e.g. a Pydantic model using
   `init_forbid_extra`/`init_typed`-sensitive syntax, or a module under a
   `[mypy-<pkg>.*]` `ignore_missing_imports` override such as `boto3` or `googleapiclient`) produces
   the same diagnostics pre-commit as it does under `scripts/verify`'s mypy invocation.
6. `git grep -- "--explicit-package-bases"` across the repository is consistent with whichever
   Agent decision this spec's implementation makes (see below) — either the flag is removed
   everywhere it was added for this workaround, or it remains and the comment explaining why is
   still accurate.

## Failure and edge cases

- If removing `backend/lambda/src/__init__.py` alone does not eliminate the ambiguity (for example
  if mypy still discovers `src` as an implicit namespace package reachable via two paths), the
  implementation must also address `mypy_path` or the invocation's working directory rather than
  reintroducing `--explicit-package-bases` as a silent fallback — falling back to the workaround
  without removing the underlying cause defeats this spec's purpose and should instead go back to
  `blocked` with the specific mypy behavior observed.
- If Poetry's build backend (via `packages = [{include = "src"}]`) requires `src/__init__.py` to
  exist for `poetry install`/`poetry export` to succeed, the implementation must resolve this by
  changing the Poetry packaging declaration (e.g. `package-mode = false`, if the installed Poetry
  version supports it, since the `src` distribution package is never actually imported by any code)
  rather than by keeping `src/__init__.py`. If neither approach can be verified against the actual
  Poetry version pinned for this project, stop and post the specific failure as a `blocked`
  question rather than guessing.
- If matching `scripts/verify`'s mypy configuration in the pre-commit hook regresses hook speed or
  requires installing the full project dependency set into the hook's isolated environment in a way
  that meaningfully slows every commit, prefer changing the hook to invoke the project's own Poetry
  virtualenv (a `language: system` hook shelling out to `cd backend/lambda && poetry run mypy
  --config-file mypy.ini ...`, mirroring how `scripts/verify` already does it) over accepting a
  weaker check.

## Architecture impact

- `backend/lambda/src/__init__.py` (and, only if still necessary after verifying the ambiguity is
  gone, other `__init__.py` files under `backend/lambda/src/`) may be removed.
- `backend/lambda/pyproject.toml`'s `[tool.poetry]` packaging declaration may change (e.g. to
  `package-mode = false`) if that is what keeps `poetry install`/`poetry export` working once
  `src/__init__.py` no longer exists.
- `.github/workflows/verify.yml` and `scripts/verify`'s mypy invocation may drop
  `--explicit-package-bases` (and its explanatory comment) once the ambiguity it works around no
  longer exists.
- `.pre-commit-config.yaml`'s mypy hook configuration changes to load `backend/lambda/mypy.ini`
  (directly or by re-pointing the hook to run from `backend/lambda`), and its
  `additional_dependencies` gains whatever packages the pydantic plugin and per-module overrides
  need to behave identically to `scripts/verify`'s invocation — or the hook is switched to a
  `language: system` hook that shells out to the project's own Poetry environment, per Failure and
  edge cases above.
- No CDK stack, API surface, DynamoDB access pattern, or Bedrock usage changes.

## Documentation impact

None. `AGENTS.md`'s existing `mypy src/` references (lines documenting local lint commands) do not
mention `--explicit-package-bases` today and remain accurate whether or not the flag is removed.

## Agent decisions

- `DERIVED`: The ambiguity's root cause is `src/__init__.py` coexisting with `mypy_path = src` —
  directly stated and diagnosed in issue #13's own investigation, confirmed by reading
  `backend/lambda/mypy.ini` and the directory structure under `backend/lambda/src/`.
- `DERIVED`: `build-lambda-packages.js` does not depend on `src` being an importable Python package
  (it copies file contents into the artifact root and relies on `sys.path`, not on `import src`) —
  confirmed by reading the script directly.
- `IMPLEMENTATION`: The exact mechanism for keeping `poetry install`/`poetry export` working once
  `src/__init__.py` is removed (switching to `package-mode = false` vs. some other Poetry packaging
  change) is left to be verified empirically at implementation time against the actual pinned
  Poetry version, per Failure and edge cases — this is a technical packaging choice within existing
  architecture, not a product/security/cost/architecture policy question, so it does not need to
  stop for a human as long as the Acceptance criteria (install/export/bundling all still work) are
  verified before merging.
- `IMPLEMENTATION`: The exact mechanism for the pre-commit mypy hook picking up
  `backend/lambda/mypy.ini` (config-file override with matching `additional_dependencies` vs. a
  `language: system` hook shelling into the project's Poetry environment) is left open, to be
  chosen based on which keeps the hook both correct and reasonably fast — again a technical choice
  within existing architecture, not a policy question.

## Open questions

None.
