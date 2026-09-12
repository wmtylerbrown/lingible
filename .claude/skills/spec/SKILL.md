---
name: spec
description: Take one GitHub issue labeled `needs-spec` to `ready` — draft the spec (a new file, or a delta recorded on the issue for a change to an implemented capability), lint it, get an isolated spec-reviewer verdict with at most one repair round, land the spec via PR, and relabel. Use whenever the user asks to "spec issue N", "write the spec for X", "draft specs for X", or names /spec directly. Also invoked by /pipeline.
---

# spec

Drive `agents/spec-agent.md` for one issue, per `docs/development/AGENT_PROTOCOL.md`. Argument:
an issue number. If none is given, ask which issue, or run `/pipeline` instead.

## 1. Claim

`git fetch origin main`. Read the issue. If it is not labeled `needs-spec`, or already carries
an `in-progress:*` label, stop and say so. Otherwise add `in-progress:spec`, remove `needs-spec`,
and comment `Pipeline claimed <RFC3339 UTC>`. Tell the user which issue you are working.

## 2. Draft (inline)

Follow `agents/spec-agent.md` in full. Decide the mode first:
- **New capability** (no `implemented` spec for it): create `spec/<slug>` from `origin/main` and
  write the spec file(s) at `status: draft` with `issue: <N>` in the front matter.
- **Retroactive spec for an already-implemented capability** (see `ROADMAP.md`): same as new
  capability, but the spec describes actual current behavior read from the code, not proposed
  behavior.
- **Change to an implemented capability**: no branch. Write the `## Proposed change` delta
  (`### ADDED` / `### MODIFIED` / `### REMOVED`) into the issue body.

An `ESCALATED` decision ends the run: post the question on the issue, swap `in-progress:spec` for
`blocked`, notify per `CLAUDE.md`, stop.

## 3. Lint

New-capability/retroactive mode: run `python3 scripts/check_specs.py --approving <spec path(s)>`
and fix every report before review. That flag applies the approval-level rules (no open questions,
cost impact stated where required) to the draft now, so nothing mechanical reaches the reviewer.

## 4. Review (isolated subagent, at most two rounds)

Invoke the `spec-reviewer` subagent with the issue number, the spec path(s) or the delta location,
and the branch. Act on the verdict:
- `PASS`: record advisory findings as an issue comment; continue.
- `FIX`: repair the blocking findings inline, then invoke the subagent once more. A second `FIX`
  ends the run: post the remaining findings on the issue, label `blocked`, notify, stop.
- `HUMAN` or `FAIL`: post the question or reason on the issue, label `blocked`, notify, stop.

## 5. Land

New-capability/retroactive mode: set `status: approved`, run `./scripts/verify`, push the branch,
open a PR titled `Spec: <title>` whose body says `Refs #<N>` (not `Closes`), using the repository
PR template. The PR title and body must not contain any GitHub closing keyword (`close`, `closes`,
`closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved`) immediately followed by
`#<N>`, in any formatting, including inside backticks or code spans — GitHub's closing-keyword
parser matches through formatting, so a spec PR that quotes the literal phrase `Closes #<N>` to
explain the convention will still auto-close the issue on squash-merge. Describe the convention in
prose ("the implementing PR closes the issue") without spelling out the phrase itself anywhere in
the PR. When CI is green, squash-merge it.

Delta mode: nothing to merge; the reviewed delta on the issue is the approved contract.

Then swap `in-progress:spec` for `ready` and end. **Do not continue into `/implement`** in this
session; `/pipeline` or a human picks the issue up separately.

## Release on any early exit

If the run stops for any reason before step 5 completes, remove `in-progress:spec` and restore
`needs-spec` (or set `blocked`, when that is the reason). Never leave an issue claimed by a run
that has ended.
