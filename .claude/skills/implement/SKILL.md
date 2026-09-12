---
name: implement
description: Take one GitHub issue labeled `ready` through implementation, isolated code review (with security attack tests and cost re-verification when required), repository verification, and delivery as a single PR that closes the issue, merging autonomously when eligible. Use whenever the user asks to "implement issue N", "build X", "pick up the next capability", or names /implement directly. Also invoked by /pipeline.
---

# implement

Drive one `ready` issue through `docs/development/AGENT_PROTOCOL.md` "Delivery". Argument: an
issue number. If none is given, ask which issue, or run `/pipeline` instead.

## 1. Claim

`git fetch origin main`. Read the issue and its spec(s) (front matter `issue: <N>`, or the delta in
the issue body for a change to an implemented capability). If the issue is not labeled `ready`, or
carries an `in-progress:*` label, stop and say so. Otherwise add `in-progress:implement`, remove
`ready`, and comment `Pipeline claimed <RFC3339 UTC>. Expected scope: <paths/dirs this will touch>`
(a short, honest guess from the issue's own description or its capability's usual area in
`ROADMAP.md` — other concurrent implement claims are checked against it). Tell the user which issue
you are working.

## 2. Freshness

Run `python3 scripts/check_spec_freshness.py <spec path>` for each spec. If it lists changed docs,
invoke the `spec-reviewer` subagent once against the spec and those docs. `PASS`: continue. `FIX`:
make the spec repair part of this PR if it is small and unambiguous; otherwise, and on `HUMAN` or
`FAIL`, post on the issue, label `blocked`, notify, release, stop.

## 3. Implement (inline)

Branch `impl/<slug>` from `origin/main`. For a delta, first apply it to the spec file in place
(edit the owning sections; no addendum). Then implement to the spec: code, tests (unit, negative
authorization, regression), and the canonical docs the spec's `affected_docs` names, edited in
their owning sections — including `docs/COST_ANALYSIS.md` when the spec's Cost impact section says
it needs updating. Record anything real but out of scope in a list for step 7; do not fix it here.

Run `./scripts/verify`. Report its exact result. Do not request review until it passes.

## 4. Review (isolated subagent, at most two rounds)

Invoke the `code-reviewer` subagent with the branch, issue, and spec path(s). Act on the verdict:
- `PASS`: continue. Record `security_test_ref` from its reply when the spec has
  `security_review: true`.
- `FIX`: fix the blocking findings, re-run `./scripts/verify`, invoke the subagent once more. A
  second `FIX` ends the run: post the findings on the issue, label `blocked`, notify, release,
  stop.
- `FAIL`: same as a second `FIX`.

## 5. Stamp

In the same branch, set the spec's `status: implemented` and `security_test_ref` (when required).
Run `python3 scripts/check_specs.py` and `./scripts/verify` once more.

## 6. Deliver

Push the branch and open a draft PR using the repository PR template, with `Closes #<N>`, the
traceability table filled from real test runs, and the review summary. Subscribe to the PR.

When CI is green:
- **Eligible** (spec `approval: autonomous`, no `HUMAN` at any stage, review `PASS`): mark ready
  for review and squash-merge. GitHub closes the issue. Remove `in-progress:implement` if it
  survived.
- **Not eligible**: leave the draft PR, comment on the issue why it waits, notify, and end. A
  human merging it completes delivery.

Red CI is this run's to fix: return to step 3.

## 7. Findings

For each out-of-scope item collected, open one issue labeled `finding` with the file, behavior,
why it matters, and a `Suggested triage:` line per `AGENT_PROTOCOL.md`. Never a spec, never a fix.
If any were filed, notify once with a pointer.

## Release on any early exit

If the run stops before merging or handing off, remove `in-progress:implement` and restore `ready`
(or set `blocked`, when that is the reason). Never leave an issue claimed by a run that has ended.
