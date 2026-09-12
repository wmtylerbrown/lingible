"""Structural/schema consistency checks for `specs/*.md`.

Each spec's own well-formedness (required front matter, required sections, no open questions on
an approved/implemented spec, decision-count/confidence/approval consistency), plus mechanical
lint rules the spec reviewer would otherwise spend rounds on, plus ROADMAP membership. Queue state
(needs-spec/ready/blocked) lives in GitHub Issues, not here -- see
docs/development/AGENT_PROTOCOL.md "Issues are the queue".

Adapted from the equivalent script on the `allong` project for Lingible's domain: Bedrock/LLM
cost review in place of allong's ride/guardian security domains, and unprefixed API routes
(`/translate`, not `/v1/translate`) in the route-handling lint rule.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
ROADMAP = ROOT / "ROADMAP.md"

REQUIRED_SECTIONS = (
    "## Intent",
    "## Existing decisions",
    "## Behavior",
    "## Actors and authorization",
    "## Privacy and data classification",
    "## Cost impact",
    "## Acceptance criteria",
    "## Failure and edge cases",
    "## Architecture impact",
    "## Documentation impact",
    "## Agent decisions",
    "## Open questions",
)

REQUIRED_KEYS = {
    "id",
    "title",
    "status",
    "approval",
    "confidence",
    "risk",
    "capability",
    "issue",
    "security_review",
    "security_domains",
    "cost_review",
    "affected_docs",
    "derived_decisions",
    "implementation_decisions",
    "escalated_decisions",
    "security_test_ref",
}

ALLOWED_STATUS = {"draft", "approved", "implemented", "retired"}
ALLOWED_APPROVAL = {"autonomous", "human_required"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_RISK = {"low", "medium", "high"}
ALLOWED_SECURITY_DOMAINS = {
    "auth",
    "authorization",
    "pii",
    "retention",
    "token",
    "iam",
    "external_service",
    "payments",
}

# Lingible's API has no version prefix (e.g. `/translate`, `/quiz/challenge`), unlike allong's
# `/v1/...`. Match an HTTP-method-prefixed route mention instead, which is how the spec template's
# Behavior guidance ("every endpoint named here states its 404/429/5xx handling") expects routes
# to be written.
ROUTE = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/\S+")


def parse_spec(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML front matter")
    try:
        _, raw_meta, body = text.split("---", 2)
    except ValueError as exc:
        raise ValueError("malformed YAML front matter") from exc
    loaded = yaml.safe_load(raw_meta)
    if not isinstance(loaded, dict):
        raise ValueError("front matter must be a mapping")
    return loaded, body.lstrip()


def roadmap_capabilities() -> set[str]:
    pattern = re.compile(r"^\| ([^|]+) \|", re.MULTILINE)
    names = {m.strip() for m in pattern.findall(ROADMAP.read_text(encoding="utf-8"))}
    return names - {"Capability", "---"}


def section(body: str, heading: str) -> str:
    if heading not in body:
        return ""
    rest = body.split(heading, 1)[1]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def main(argv: list[str]) -> int:
    approving: set[Path] = set()
    if argv:
        if argv[0] != "--approving" or len(argv) < 2:
            print(__doc__)
            return 2
        approving = {(ROOT / a).resolve() for a in argv[1:]}

    errors: list[str] = []
    capabilities = roadmap_capabilities()
    seen_ids: dict[str, Path] = {}
    real = 0

    for path in sorted(SPECS.glob("*.md")):
        if path.name == "TEMPLATE.md":
            continue
        rel = path.relative_to(ROOT)

        try:
            meta, body = parse_spec(path)
        except ValueError as exc:
            errors.append(f"{rel}: {exc}")
            continue
        real += 1

        missing = REQUIRED_KEYS - meta.keys()
        if missing:
            errors.append(f"{rel}: missing metadata keys {sorted(missing)}")
        extra = meta.keys() - REQUIRED_KEYS
        if extra:
            errors.append(f"{rel}: unknown metadata keys {sorted(extra)}")

        for heading in REQUIRED_SECTIONS:
            if heading not in body:
                errors.append(f"{rel}: missing section {heading}")

        status = meta.get("status")
        if path.resolve() in approving and status == "draft":
            status = "approved"
        approval = meta.get("approval")
        confidence = meta.get("confidence")
        risk = meta.get("risk")
        capability = meta.get("capability")
        issue = meta.get("issue")
        security_review = meta.get("security_review")
        security_domains = meta.get("security_domains")
        cost_review = meta.get("cost_review")
        affected_docs = meta.get("affected_docs")
        escalated = meta.get("escalated_decisions")
        spec_id = meta.get("id")

        if isinstance(spec_id, str):
            if spec_id in seen_ids:
                errors.append(f"{rel}: duplicate id {spec_id!r} (also {seen_ids[spec_id]})")
            seen_ids[spec_id] = rel

        if status not in ALLOWED_STATUS:
            errors.append(f"{rel}: invalid status {status!r}")
        if approval not in ALLOWED_APPROVAL:
            errors.append(f"{rel}: invalid approval {approval!r}")
        if confidence not in ALLOWED_CONFIDENCE:
            errors.append(f"{rel}: invalid confidence {confidence!r}")
        if risk not in ALLOWED_RISK:
            errors.append(f"{rel}: invalid risk {risk!r}")
        if issue is not None and not (isinstance(issue, int) and issue > 0):
            errors.append(f"{rel}: issue must be a positive integer or null")

        if status != "retired" and (
            not isinstance(capability, str) or capability not in capabilities
        ):
            errors.append(f"{rel}: capability {capability!r} is not a ROADMAP capability")

        if not isinstance(affected_docs, list):
            errors.append(f"{rel}: affected_docs must be a list")
        else:
            for raw in affected_docs:
                if not isinstance(raw, str):
                    errors.append(f"{rel}: affected_docs contains non-string {raw!r}")
                elif not (ROOT / raw).exists():
                    errors.append(f"{rel}: affected_docs path does not exist: {raw}")

        if not isinstance(security_domains, list):
            errors.append(f"{rel}: security_domains must be a list")
        else:
            unknown = set(security_domains) - ALLOWED_SECURITY_DOMAINS
            if unknown:
                errors.append(f"{rel}: unknown security_domains {sorted(unknown)}")
            if security_domains and security_review is not True:
                errors.append(f"{rel}: security_domains require security_review: true")

        if risk == "high" and security_review is not True:
            errors.append(f"{rel}: high-risk spec requires security_review: true")

        if not isinstance(cost_review, bool):
            errors.append(f"{rel}: cost_review must be true or false")
        else:
            cost_impact = section(body, "## Cost impact").strip()
            no_cost_impact = cost_impact.lower() in {"", "none", "none.", "n/a", "n/a."}
            if cost_review and no_cost_impact:
                errors.append(
                    f"{rel}: cost_review: true requires a non-empty Cost impact section"
                )
            if not cost_review and not no_cost_impact:
                errors.append(
                    f"{rel}: Cost impact section is filled in but cost_review is not true"
                )

        # Declaring security review is not executing it: an implemented security-sensitive spec
        # must point at the attack tests that actually ran.
        if security_review is True and status == "implemented":
            test_ref = meta.get("security_test_ref")
            if not test_ref:
                errors.append(
                    f"{rel}: security_review spec marked implemented without security_test_ref"
                )
            elif isinstance(test_ref, str) and not (ROOT / test_ref).exists():
                errors.append(f"{rel}: security_test_ref path does not exist: {test_ref}")

        if not isinstance(escalated, int) or escalated < 0:
            errors.append(f"{rel}: escalated_decisions must be a non-negative integer")

        open_questions = section(body, "## Open questions").strip()
        no_open_questions = open_questions.lower() in {"", "none", "none.", "n/a", "n/a."}
        if status in {"approved", "implemented"} and not no_open_questions:
            errors.append(f"{rel}: {status} spec still has open questions")

        if approval == "autonomous":
            if confidence == "low":
                errors.append(f"{rel}: low-confidence spec cannot be autonomous")
            if isinstance(escalated, int) and escalated > 0:
                errors.append(f"{rel}: autonomous approval cannot retain escalated decisions")

        # Lint: an approved spec (or a draft being linted with --approving) whose Behavior names
        # an API route must state its 404/429/5xx handling. Formerly a recurring reviewer finding;
        # now mechanical. Retroactive specs for capabilities implemented before this pipeline
        # existed are not retroactively held to it if the code predates it -- use judgment.
        if (
            status == "approved"
            and ROUTE.search(section(body, "## Behavior"))
            and ("404" not in body or not re.search(r"429|5xx", body))
        ):
            errors.append(f"{rel}: names routes but does not state 404 and 429/5xx handling")

    if errors:
        print("Spec consistency check FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Spec consistency check passed ({real} real spec(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
