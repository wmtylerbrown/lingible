---
id: SPEC-INFRA-TOOLCHAIN-001
title: Backend Python toolchain (uv + ruff + nox)
status: approved
approval: autonomous
confidence: high
risk: medium
capability: "Infrastructure & deployment (CDK: Shared/Data/Async/Api/Website stacks)"
issue: 12
security_review: false
security_domains: []
cost_review: false
affected_docs: ["AGENTS.md", "backend/scripts/setup-uv.sh", "scripts/verify"]
derived_decisions: 6
implementation_decisions: 6
escalated_decisions: 0
security_test_ref: null
---

# Backend Python toolchain (uv + ruff + nox)

## Intent

`backend/lambda` uses Poetry (dependency management + lockfile), flake8 (lint, with no committed
config, so CI silently runs at flake8's own defaults rather than the 88-column width the project
actually intends — see Existing decisions), Black (formatting), and mypy, invoked ad hoc from
`scripts/verify`, `.github/workflows/verify.yml`, and `.pre-commit-config.yaml`. `allong`
(`/Users/tyler/Projects/allong`) already runs a proven, locked, reproducible equivalent: `uv` for
dependency resolution and installs, `ruff` for both lint and format, and `nox` sessions as the
single task-runner surface, with `uv`'s own lockfile (`uv.lock`) providing hash-verified,
reproducible installs natively.

Separately, `backend/cdk/src/constructs/shared-construct.ts`'s `createDependencyLayer` currently
installs each Lambda layer's dependencies inside a Docker container (CDK's
`bundlingImage`/`bundling` mechanism) by running `pip install --platform manylinux2014_aarch64
--implementation cp --python-version 3.13 --only-binary=:all: --target ... -r requirements.txt`.
That `pip` invocation is already a pure cross-platform wheel *download* (`--platform` +
`--only-binary=:all:` fetch prebuilt manylinux wheels from PyPI; nothing is compiled), so it does
not actually need to execute inside a Linux container — it only needs a `pip`/`uv` binary capable
of resolving wheels for a foreign platform, which runs identically on a Mac host. `allong`'s
`backend/scripts/build_lambda_layer.py` proves this pattern already: it runs the equivalent `uv pip
install --python-platform x86_64-unknown-linux-gnu --python-version 3.13 --only-binary :all:
--target ...` as a plain host-side script, and its CDK app then does a plain
`lambda.Code.fromAsset(preBuiltDir)` with no `bundling` block and no Docker daemon requirement.

This spec covers replacing Poetry/flake8/Black with uv/ruff (plus introducing `nox` sessions
mirroring `allong`'s for the Python-only tasks), and replacing the CDK Docker-bundling step for
Lambda dependency layers with a host-side `uv pip install --python-platform ...` step run by
`backend/cdk/scripts/build-lambda-packages.js` before `cdk synth`/`cdk deploy` — matching the
sequencing `predeploy`/`build:lambdas` already uses today, just without Docker. It also resolves
issue #22 (`poetry export` requiring the separate, undeclared `poetry-plugin-export` package as of
Poetry 2.x) as a side effect, since `uv export` is a built-in uv command.

This spec does not change: mypy's configured strictness (`backend/lambda/mypy.ini`'s existing
lenient settings carry over unchanged — only the tool invoking mypy changes, from `poetry run mypy`
to `uv run mypy`), any Lambda's runtime behavior, any Lambda's declared dependency versions beyond
what re-resolving with `uv` naturally produces, or the CDK Lambda function architecture
(`arm64`, per `python-lambda.ts`).

## Existing decisions

- `AGENTS.md`: project convention is one venv at the repo root (`.venv`), activated via
  `source .venv/bin/activate`, with `PYTHONPATH=backend/lambda/src` for local dev/test; Poetry is
  currently documented as run "from `backend/lambda/` directory with activated venv."
- `backend/lambda/pyproject.toml`: Poetry-managed, Python `^3.13`, three dependency groups beyond
  the implicit main group — `dev` (pytest, pytest-mock, moto, black, flake8, mypy, type stubs,
  pre-commit), `receipt-validation` (`app-store-server-library`), `slang-validation`
  (`tavily-python`) — consumed selectively per Lambda layer via `poetry export --with <group>`.
- `backend/cdk/scripts/build-lambda-packages.js`: generates one `requirements.txt` per layer
  (`core` = main group only, `receipt-validation` = main + receipt-validation,
  `slang-validation` = main + slang-validation) via `poetry export`, then leaves the actual
  dependency install to CDK's bundling step.
- `backend/cdk/src/constructs/shared-construct.ts` `createDependencyLayer`: installs each layer's
  `requirements.txt` inside a `lambda.Runtime.PYTHON_3_13.bundlingImage` Docker container, using
  `pip install --platform manylinux2014_aarch64 --implementation cp --python-version 3.13
  --only-binary=:all:` — confirmed by direct inspection to be resolving prebuilt wheels only, never
  compiling.
- `backend/cdk/src/components/lambda/python-lambda.ts`: every Lambda function runs
  `architecture: lambda.Architecture.ARM_64`, `runtime: lambda.Runtime.PYTHON_3_13`; per-handler
  code assets are copied verbatim (`cp handler.py`), not dependency-installed, and are unaffected
  by this spec.
- `scripts/verify` and `.github/workflows/verify.yml` (both from #11) run, for `backend/lambda`:
  `poetry install`, `pytest`, `mypy src/`, `flake8 src/` — with no committed flake8 config, so
  `flake8 src/` runs at flake8's own default (79-column) line length, while
  `.pre-commit-config.yaml`'s flake8 hook separately passes `--max-line-length=88` (matching
  Black's `--line-length=88` pre-commit arg) — these two enforcement paths currently disagree, and
  neither `scripts/verify` nor CI notices because flake8's *default* is stricter, not looser, so a
  file that already satisfies 88-column pre-commit still trivially satisfies bare `flake8 src/`'s
  own defaults on unrelated rules, masking the gap. This spec's `ruff` migration uses a single
  checked-in config for lint and format, closing this gap as a byproduct.
- `.pre-commit-config.yaml`: Black + flake8 + a `language: system` mypy hook shelling into
  `backend/lambda`'s Poetry environment (per `specs/mypy-package-identity-fix.md`, so it reads
  `backend/lambda/mypy.ini`'s pydantic plugin and per-module overrides, not a bare
  `--ignore-missing-imports` run).
- `backend/scripts/setup-poetry.sh`: documented onboarding path, installs Poetry then runs
  `poetry install` from `backend/lambda`.
- `allong`'s `noxfile.py`, `scripts/bootstrap`, and `backend/scripts/build_lambda_layer.py`
  (`/Users/tyler/Projects/allong`) are the reference implementation this spec ports from, adapted
  to Lingible's existing structure (one `scripts/verify` entry point covering both
  `backend/lambda` and `backend/cdk`, not allong's split `test_app`/`test_infra`/`docs` sessions,
  which don't apply here — Lingible's CDK app has no CDK-synthesis-dependent test suite today).
- `docs/development/AGENT_PROTOCOL.md` "Deploys stay separate from CI": `npm run deploy:dev`/
  `deploy:prod` (which run `predeploy` → `build:lambdas` → `cdk deploy`) remain the only path to
  AWS; this spec does not change that boundary, only what `build:lambdas` and the CDK layer
  construct do internally.

## Behavior

- `backend/lambda` is managed by `uv` instead of Poetry: dependency declarations move from
  `[tool.poetry.dependencies]`/`[tool.poetry.group.*.dependencies]` to PEP 621 `[project]`
  metadata plus groups/extras (see Agent decisions for the exact split), and `poetry.lock` is
  replaced by `uv.lock`, which uv generates and verifies automatically (hash-verified installs are
  uv's default behavior for a `uv.lock`-backed project — no separate hash-locking mechanism needs
  to be designed or opted into).
- `uv sync` (or the project's bootstrap script wrapping it) installs the repo-root `.venv` exactly
  as `poetry install` does today: same venv location, same `PYTHONPATH=backend/lambda/src`
  convention, same `ENVIRONMENT=test` convention for tests — none of these change.
- Lint and format for `backend/lambda/src` run via `ruff check` and `ruff format` (a single tool,
  replacing both flake8 and Black), configured in `backend/lambda/pyproject.toml`'s `[tool.ruff]`
  table, with `line-length = 88` (matching the project's existing, previously-unenforced 88-column
  intent) and the same `src/utils/slang_words.py` exclusion the current flake8/mypy hooks already
  carry.
- Type checking continues to run `mypy` against `backend/lambda/src`, reading the unchanged
  `backend/lambda/mypy.ini`, invoked as `uv run mypy` instead of `poetry run mypy` — no rule,
  strictness, or plugin configuration changes.
- `nox` (config at the repo root, `noxfile.py`) exposes at least `lint`, `typecheck`, and `test`
  sessions for `backend/lambda`, each backed by `venv_backend="none"` running the repo's own
  `.venv` binaries directly (mirroring `allong`'s pattern), plus a `verify` session that runs all
  of them. `scripts/verify` and `.github/workflows/verify.yml`'s backend job invoke these nox
  sessions instead of separate `poetry run ...` lines, for a single definition of "what backend
  lint/typecheck/test means" shared between local dev, pre-commit, `scripts/verify`, and CI.
- `.pre-commit-config.yaml`'s Black and flake8 hooks are replaced by `ruff-pre-commit`'s
  `ruff-format` and `ruff` (lint, `--fix`) hooks pinned to the same ruff version `pyproject.toml`
  declares; the existing `language: system` mypy hook is updated to invoke `uv run mypy` (or the
  repo `.venv`'s `mypy` binary directly) instead of `poetry run mypy`, with no other change to that
  hook.
- `backend/cdk/scripts/build-lambda-packages.js`:
  - generates each layer's `requirements.txt` via `uv export` (from `backend/lambda`, targeting
    the appropriate group/extra per layer — see Agent decisions) instead of `poetry export`.
  - additionally performs the dependency **install** itself, host-side, via `uv pip install
    --python-platform aarch64-unknown-linux-gnu --python-version 3.13 --only-binary=:all:
    --target <layer-dir>/python -r requirements.txt` (matching the existing
    `manylinux2014_aarch64`/`arm64` target), writing directly into each layer's artifact directory
    under a `python/` subdirectory — the same directory shape `pip install --target` inside the
    old Docker bundling step already produced.
- `backend/cdk/src/constructs/shared-construct.ts` `createDependencyLayer` no longer declares a
  `bundling` block; it becomes `lambda.Code.fromAsset(assetPath)` pointing at the same artifact
  directory `build-lambda-packages.js` now populates directly (already containing `python/` with
  the installed dependencies), matching how `createSourceLayer` already works (no bundling).
  Neither `cdk synth` nor `cdk deploy` requires a Docker daemon as a result of this spec's change
  (no other part of the CDK app uses Docker bundling — `python-lambda.ts`'s per-handler asset copy
  is unaffected by this spec and is out of scope here).
- `backend/scripts/setup-poetry.sh` is replaced by an equivalent `backend/scripts/setup-uv.sh` (or
  renamed in place) that installs `uv` if missing, creates/updates the repo-root `.venv` via
  `uv venv`/`uv sync`, and prints the same category of next-steps guidance the current script
  does, updated for `uv`/`nox` commands.
- `AGENTS.md`'s dependency-management instructions are updated to describe `uv` (e.g.
  `uv add <package>` from `backend/lambda`, `uv sync`) instead of Poetry, and its stale
  `pip install -r backend/lambda/requirements.txt` "complete setup from scratch" line is corrected
  to the actual bootstrap path.

## Actors and authorization

None — this is development/build tooling with no runtime actor, request, or authorization surface.
No IAM, API, or Lambda runtime permission changes.

## Privacy and data classification

None. No PII or persisted application data is read or written by this change.

## Cost impact

None.

## Acceptance criteria

1. From a clean checkout with only `uv` installed (no Poetry required), the project's bootstrap
   script produces a working `.venv` at the repo root, and `PYTHONPATH=backend/lambda/src
   ENVIRONMENT=test <venv>/bin/pytest backend/lambda/tests/` passes with the same test results as
   before this change (no test added, removed, or changed in behavior by this spec).
2. `nox -s lint` and `nox -s typecheck` both exit 0 against the current `backend/lambda/src` tree
   (after any mechanical reformatting `ruff format` itself applies) and would each independently
   report the same class of finding on a deliberately introduced lint/type error as the tool it
   replaces did (a flake8-style unused import is still flagged by `ruff check`; a mypy error under
   an existing per-module override still surfaces under `uv run mypy`).
3. `scripts/verify` passes end to end using only `uv`/`nox` for the `backend/lambda` portion — no
   step in the updated script shells out to `poetry`.
4. `.github/workflows/verify.yml`'s backend job passes on a fresh runner using only `uv` (installed
   via an official uv GitHub Action or equivalent) — no `pip install poetry` step remains for the
   backend job.
5. `git grep -rn "poetry"` across `backend/`, `scripts/`, `.github/workflows/verify.yml`,
   `.pre-commit-config.yaml`, and `AGENTS.md` returns no remaining operational references (comments
   describing history, e.g. in this spec or in `specs/mypy-package-identity-fix.md`, are not in
   scope and may remain).
6. `node backend/cdk/scripts/build-lambda-packages.js` (or its equivalent invocation via
   `npm run build:lambdas`), run on a host with **no Docker daemon running**, succeeds and produces
   each layer artifact directory containing a populated `python/` subdirectory with the correct
   arm64/manylinux wheels for that layer's dependency set (`core`, `receipt-validation`,
   `slang-validation` each contain their own group's packages, matching today's per-layer
   dependency split).
7. `cdk synth` (via `npm run synth:dev` or equivalent), run immediately after acceptance criterion
   6 with no Docker daemon running, succeeds and produces a template referencing Lambda layers
   built from the pre-populated artifact directories — `git grep -n "bundlingImage" backend/cdk/src`
   no longer matches `shared-construct.ts`'s dependency-layer construction.
8. Issue #22 is resolved as a consequence: nothing in the updated toolchain invokes
   `poetry export` or depends on `poetry-plugin-export`.

## Failure and edge cases

- If `uv export`'s exact flags/behavior for producing a `requirements.txt` scoped to one extra/group
  (without pulling in the `dev` group or other extras) differ from what's assumed above for the
  pinned `uv` version, the implementation must verify the actual output empirically (compare
  against today's `poetry export --with <group>` output for the same layer) before relying on it,
  rather than assuming flag compatibility — this is an `IMPLEMENTATION`-level detail to verify at
  build time, not a reason to fall back to `poetry export`.
- If `uv pip install --python-platform aarch64-unknown-linux-gnu --only-binary=:all:` cannot find a
  compatible prebuilt wheel for some pinned dependency version (a package that only ships sdists,
  or only manylinux2014/2010 x86_64 wheels), the build must fail loudly with the missing package
  named (mirroring `allong`'s `build_lambda_layer.py`'s explicit `BuildError`), not silently fall
  back to compiling or to a different platform tag. If this happens for a real Lingible dependency,
  stop and post the specific package/version as a `blocked` finding rather than guessing a
  workaround.
- If moving the actual `pip`/`uv` install into `build-lambda-packages.js` meaningfully increases
  that script's runtime versus the current "generate requirements.txt only, let Docker/CDK install"
  split (since the install now always runs host-side even when `cdk deploy` itself would have
  skipped an unchanged layer), preserve the existing hash-based skip logic
  (`build-lambda-packages.js`'s `HASH_FILE` mechanism) so an unchanged layer's dependency set is not
  reinstalled on every `predeploy` run.
- If any Lingible developer's machine cannot run `uv pip install --python-platform
  aarch64-unknown-linux-gnu` for a reason specific to their host (e.g. an old `uv` version without
  cross-platform resolution support), the fix is to bump the required `uv` version (pinned in
  `backend/scripts/setup-uv.sh`/bootstrap and CI), not to reintroduce Docker bundling as a fallback
  path.

## Architecture impact

- `backend/lambda/pyproject.toml`: Poetry tables replaced by PEP 621 `[project]` +
  `[dependency-groups]`/`[project.optional-dependencies]` (see Agent decisions) plus new
  `[tool.ruff]` and unchanged `[tool.mypy]`-equivalent config (mypy continues to read
  `backend/lambda/mypy.ini` directly; `pyproject.toml` does not need to duplicate it). `poetry.lock`
  removed; `uv.lock` added.
- `backend/scripts/setup-poetry.sh` replaced/renamed; `backend/scripts/setup-uv.sh` (or similar)
  added.
- `noxfile.py` added at the repo root.
- `backend/cdk/scripts/build-lambda-packages.js`: `poetry export` calls replaced with `uv export`;
  new host-side `uv pip install --python-platform ... --target` step added per layer.
- `backend/cdk/src/constructs/shared-construct.ts`: `createDependencyLayer`'s `bundling` block
  removed; becomes a plain `lambda.Code.fromAsset(assetPath)`, matching `createSourceLayer`.
- `.github/workflows/verify.yml`: backend job's Poetry install/cache steps replaced with a uv
  setup/cache step (e.g. `astral-sh/setup-uv`), and the pytest/mypy/flake8 steps replaced with
  `nox -s test typecheck lint` (or the equivalent explicit `uv run` commands, whichever the
  implementation finds keeps CI output most legible per-step — an `IMPLEMENTATION` choice).
- `.pre-commit-config.yaml`: Black + flake8 hooks replaced with `ruff-pre-commit`'s hooks; the
  existing local mypy hook's `entry` changes from `poetry run mypy` to a `uv run mypy`/`.venv`
  equivalent.
- No API, DynamoDB access-pattern, IAM, or Bedrock/LLM usage change of any kind.

## Documentation impact

- `AGENTS.md`: dependency-management section (currently describing Poetry commands) updated to
  describe `uv` equivalents; the stale `pip install -r backend/lambda/requirements.txt`
  "complete setup from scratch" example corrected.
- `scripts/verify`'s header comment (which currently explicitly contrasts Lingible's Poetry-based
  approach with `allong`'s uv/nox/locked toolchain, calling the difference deliberate) updated to
  reflect that they now match, and the comment explaining why removed or corrected.
- `backend/scripts/setup-poetry.sh` → its replacement's content, referenced wherever the old
  filename was documented (if anywhere outside `AGENTS.md`).

## Agent decisions

- `DERIVED`: The CDK Docker-bundling step for Lambda dependency layers performs pure wheel
  resolution (`--platform`/`--only-binary=:all:`), never compilation — confirmed by reading
  `shared-construct.ts`'s exact `pip install` command — so it can run host-side without a
  container, exactly as `allong`'s `build_lambda_layer.py` already does for the equivalent
  `pydantic`/`pydantic-core` native-extension dependency.
- `DERIVED`: `uv.lock` provides hash-verified installs by default, so issue #12's open question
  "decide whether to hash-lock the toolchain" is resolved by the choice of `uv` itself — no
  separate `--generate-hashes` step or opt-in decision is needed, unlike the Poetry status quo.
- `DERIVED`: Migrating to `uv` removes the `poetry export`/`poetry-plugin-export` dependency
  entirely (`uv export` is a built-in uv command), resolving issue #22 as a consequence rather than
  requiring separate work.
- `DERIVED`: `.github/workflows/verify.yml`'s `cdk-build` and other jobs never invoke `cdk synth`
  (only `npm run build`, a plain `tsc` compile) and `npm run test` invokes only
  `verify-bedrock-resources.ts` (no CDK synth either) — confirmed by reading
  `backend/cdk/package.json` and the workflow file — so today's CI never exercises the Docker
  bundling path at all; removing it changes only `npm run deploy:dev`/`deploy:prod` and local
  `cdk synth`, not CI.
- `IMPLEMENTATION`: Poetry's `[tool.poetry.group.dev.dependencies]` (pytest, mypy, ruff/ex-flake8,
  pre-commit, etc. — pure dev/test tooling, never installed into a deployed Lambda artifact) maps
  to PEP 735 `[dependency-groups] dev = [...]`. Poetry's `receipt-validation` and
  `slang-validation` groups (each an additive *runtime* dependency set bundled into a specific
  Lambda layer, per `build-lambda-packages.js`'s `LAYER_CONFIGS`) map to
  `[project.optional-dependencies]` extras of the same names, since they are runtime extras rather
  than dev-only tooling — mirroring the semantic split `allong`'s own `pyproject.toml` already uses
  between its `dev` dependency group and its `infra` optional-dependency extra. This is a technical
  mapping choice within uv's existing PEP 621/735 support, not a product/architecture policy.
- `IMPLEMENTATION`: Whether `backend/lambda/pyproject.toml` keeps a `[build-system]`
  (hatchling, matching `allong`) or instead sets `[tool.uv] package = false` (since no code in this
  repo is ever installed as an importable `lingible-backend`/`src` package — `build-lambda-packages.js`
  copies file contents directly, per `specs/mypy-package-identity-fix.md`'s existing finding) is
  left to be resolved empirically at implementation time, choosing whichever keeps `uv sync`/
  `uv export` simplest without reintroducing the package-identity ambiguity #13 already fixed.
- `IMPLEMENTATION`: The exact `nox` session boundaries (separate `lint`/`format` sessions vs. one
  combined `lint` session running both `ruff check` and `ruff format --check`) and whether
  `scripts/verify` calls `nox -s verify` as one step or calls each session individually for clearer
  CI step-by-step output are left to the implementation, matching `allong`'s pattern where it
  produces equivalent-or-better output legibility.
- `IMPLEMENTATION`: Whether CI's uv setup uses the `astral-sh/setup-uv` GitHub Action (with its own
  caching) or a plain `pip install uv`/curl-installer step is left to the implementation, choosing
  whichever the pinned `uv` version and existing cache-key conventions in
  `.github/workflows/verify.yml` support most simply.
- `IMPLEMENTATION`: The exact wheel-count/runtime cost of moving the dependency install into
  `build-lambda-packages.js` (vs. today's split where Docker did the install) is expected to be a
  local build-time change only, bounded by the existing hash-skip logic (see Failure and edge
  cases) — not something requiring a policy decision, since it has no effect on deployed behavior,
  cost, or CI.

## Open questions

None.
