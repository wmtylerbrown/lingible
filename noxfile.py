"""Task definitions for backend/lambda's Python toolchain (uv-managed).

Every session assumes the repo-root `.venv` already exists (`uv sync --project backend/lambda`,
or `backend/scripts/setup-uv.sh`). Sessions call that venv's own binaries directly rather than
letting nox manage its own environments, so they stay bound to the exact locked toolchain in
`backend/lambda/uv.lock` -- see specs/backend-python-toolchain.md.

Ported from allong (/Users/tyler/Projects/allong/noxfile.py), simplified: Lingible's CDK app has
no CDK-synthesis-dependent test suite today, so there is no test_app/test_infra split, and
`scripts/verify` (not nox) remains the single cross-language entry point covering backend/cdk
(npm/tsc) and the repo-wide spec/cost-review checks -- these nox sessions cover only the Python
portion, backend/lambda.
"""

from __future__ import annotations

from pathlib import Path

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.default_venv_backend = "none"

ROOT = Path(__file__).resolve().parent
LAMBDA_DIR = ROOT / "backend" / "lambda"
VENV_BIN = ROOT / ".venv" / "bin"


def _venv(tool: str) -> str:
    return str(VENV_BIN / tool)


@nox.session(venv_backend="none")
def lint(session: nox.Session) -> None:
    """ruff check + ruff format --check over backend/lambda/src."""
    with session.chdir(LAMBDA_DIR):
        session.run(_venv("ruff"), "check", "src", external=True)
        session.run(_venv("ruff"), "format", "--check", "src", external=True)


@nox.session(venv_backend="none")
def typecheck(session: nox.Session) -> None:
    """mypy over backend/lambda/src, reading backend/lambda/mypy.ini."""
    with session.chdir(LAMBDA_DIR):
        session.run(_venv("mypy"), "src", external=True)


@nox.session(venv_backend="none")
def test(session: nox.Session) -> None:
    """pytest over backend/lambda/tests."""
    with session.chdir(LAMBDA_DIR):
        session.run(
            _venv("pytest"),
            "tests",
            "-q",
            external=True,
            env={"ENVIRONMENT": "test", "PYTHONPATH": "src"},
        )


@nox.session(venv_backend="none")
def verify(session: nox.Session) -> None:
    """Everything backend/lambda's portion of scripts/verify needs."""
    session.notify("lint")
    session.notify("typecheck")
    session.notify("test")
