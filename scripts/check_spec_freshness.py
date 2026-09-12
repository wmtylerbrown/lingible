"""Report which of a spec's cited documents changed since the spec itself last changed.

Usage: python3 scripts/check_spec_freshness.py specs/<file>.md [...]

Exit 0 and print nothing when every `affected_docs` entry is untouched since the spec's last
commit; exit 1 and list the changed paths otherwise. The /implement skill runs the isolated spec
reviewer once against those docs before writing code (AGENT_PROTOCOL.md "Delivery"). This replaces
the old always-on pre-implementation re-verification: only a spec whose inputs actually moved pays
for a review.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    stale = False
    for arg in argv:
        spec = ROOT / arg
        meta = yaml.safe_load(spec.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        base = git("log", "-1", "--format=%H", "--", str(spec.relative_to(ROOT))).strip()
        if not base:
            print(f"{arg}: not committed yet; nothing to compare against")
            continue
        for doc in meta.get("affected_docs") or []:
            changed = git("log", "--format=%h %s", f"{base}..HEAD", "--", doc).strip()
            if changed:
                stale = True
                print(f"{arg}: {doc} changed since {base[:8]}:")
                for line in changed.splitlines():
                    print(f"    {line}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
