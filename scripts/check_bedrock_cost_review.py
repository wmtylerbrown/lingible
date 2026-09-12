"""Mechanical backstop: a diff touching Bedrock-cost-relevant code must also touch
`docs/COST_ANALYSIS.md`.

This exists because the spec-level `cost_review` field (docs/development/AGENT_PROTOCOL.md "Cost
impact") only catches a cost regression if the spec correctly predicted the change would touch
Bedrock. This script doesn't trust that prediction -- it looks at the actual diff, two ways:

1. **Known files** (WATCHED below): the existing Bedrock call sites and cost-relevant config.
   Extend this list whenever a new call site is added there -- an unlisted *known* file touching
   Bedrock cost is a bug in this list.
2. **Content signatures** (BEDROCK_SIGNATURES below): every added/changed line across the whole
   diff, not just WATCHED files, is scanned for signs of a Bedrock call -- `invoke_model`,
   `bedrock_client`, `anthropic_version`, a Bedrock `modelId=`. This is what catches a *new* file
   that starts calling Bedrock for the first time (a new feature's own service module, say) even
   though nobody added it to WATCHED yet -- the alternative, trusting only a hand-maintained file
   list, silently misses exactly that case.

Either kind of hit, with no corresponding touch of `docs/COST_ANALYSIS.md` in the same diff, fails
the check. This is a deliberately blunt instrument: it will sometimes ask for a
`docs/COST_ANALYSIS.md` touch that turns out to be "no change needed" (e.g. a pure refactor that
doesn't change token counts, model, or call volume) -- in that case, edit the doc to add one line
under "Recent changes reviewed" (see the doc) saying so and why, rather than skipping the check.
That edit is exactly what makes the check pass, and it also becomes the record that a human/agent
actually looked. A content-signature hit on a file already in WATCHED is reported once, not twice
-- and is also a prompt to add that file to WATCHED so future changes to it are named explicitly
rather than relying on the signature scan alone.

Usage: python3 scripts/check_bedrock_cost_review.py [<base-ref>]

Compares <base-ref> (default: origin/main) against HEAD. Exits 0 (silently) when nothing
Bedrock-relevant changed, or when something did and docs/COST_ANALYSIS.md changed too. Exits 1
with an explanation otherwise.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Every known file whose change plausibly moves Lingible's per-request Bedrock cost: the LLM call
# sites, the model/prompt/tier-limit configuration, and the config model that shapes them.
WATCHED = (
    "backend/lambda/src/services/slang_llm_service.py",
    "backend/lambda/src/services/slang_validation_service.py",
    "backend/lambda/src/services/trending_service.py",
    "backend/lambda/src/models/config.py",
    "shared/config/backend/dev.json",
    "shared/config/backend/prod.json",
)

# Substrings that, in an added/changed line anywhere in the diff, indicate a Bedrock call --
# regardless of which file they appear in. Catches a new file nobody added to WATCHED yet.
BEDROCK_SIGNATURES = (
    "invoke_model",
    "bedrock_client",
    "anthropic_version",
    "bedrock-runtime",
)

COST_DOC = "docs/COST_ANALYSIS.md"


def run_git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def changed_files(base: str) -> set[str]:
    out = run_git("diff", "--name-only", f"{base}...HEAD")
    return {line.strip() for line in out.splitlines() if line.strip()}


SELF_PATH = "scripts/check_bedrock_cost_review.py"  # its own docstring names its signatures


def files_with_bedrock_signatures(base: str) -> set[str]:
    """Files (any path) whose added/changed lines contain a Bedrock-call signature."""
    diff = run_git("diff", "-U0", f"{base}...HEAD")
    hits: set[str] = set()
    current_file: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[len("+++ b/") :].strip()
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if current_file and current_file != SELF_PATH and any(
            sig in line for sig in BEDROCK_SIGNATURES
        ):
            hits.add(current_file)
    return hits


def main(argv: list[str]) -> int:
    base = argv[0] if argv else "origin/main"
    try:
        files = changed_files(base)
        signature_hits = files_with_bedrock_signatures(base)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: could not diff against {base!r}: {exc.stderr.strip()}", file=sys.stderr)
        return 2

    watched_hit = {f for f in WATCHED if f in files}
    all_hits = sorted(watched_hit | signature_hits)

    if not all_hits:
        print("No Bedrock-cost-relevant files changed.")
        return 0

    new_via_signature = sorted(signature_hits - watched_hit)

    if COST_DOC in files:
        print(
            f"Bedrock-cost-relevant file(s) changed ({', '.join(all_hits)}) and "
            f"{COST_DOC} was also updated in this diff. OK."
        )
        if new_via_signature:
            print(
                "  Note: "
                + ", ".join(new_via_signature)
                + " matched a Bedrock-call signature but is not in WATCHED in "
                "scripts/check_bedrock_cost_review.py -- consider adding it so future changes "
                "are named explicitly."
            )
        return 0

    print("Bedrock cost review check FAILED:")
    print(f"  Changed file(s) that can affect per-request Bedrock cost: {', '.join(all_hits)}")
    if new_via_signature:
        print(
            f"  ({', '.join(new_via_signature)} matched a Bedrock-call signature and is not yet "
            "in WATCHED -- add it there too.)"
        )
    print(f"  {COST_DOC} was not touched in this diff.")
    print()
    print(
        "  Update docs/COST_ANALYSIS.md with the actual cost impact (or a one-line note that this "
        "specific change has none, with why), then re-run this check."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
