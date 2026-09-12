---
name: pipeline
description: Do the next unit of pipeline work in one lane. The implement lane picks the next eligible `ready` issue and runs /implement; the spec lane picks the next eligible `needs-spec` issue and runs /spec. Each lane is single-flight, so at most one implement run and one spec run are active at a time. Exits cheaply if the lane is busy or nothing is eligible. Use whenever the user says "keep the pipeline moving", "do the next thing", "work the queue", or names /pipeline.
---

# pipeline

One unit of work per invocation, in one lane. Never two.

Argument: `implement` or `spec`, naming the lane. With no argument, try `implement` first and fall
through to `spec` only when the implement lane is busy or has nothing eligible. Either way the
invocation does at most one unit of work.

## 1. Orient

`git fetch origin main` and read `ROADMAP.md` from `origin/main` (the capability table and its
"Depends on" column). List open issues with the GitHub tools available to this session.

## 2. Lane check

Each lane has its own claim label: `in-progress:implement` and `in-progress:spec`. If any open
issue carries this lane's label:
- read its `Pipeline claimed <timestamp>` comment;
- if the claim is under three hours old, or an open PR references the issue, **stop**: report
  which issue holds the lane and end;
- otherwise the claim is stale: remove the lane label, restore `ready` (implement lane) or
  `needs-spec` (spec lane), and continue.

The other lane's claim is not this run's concern. A draft PR waiting on a human holds the
implement lane only; the spec lane keeps moving.

## 3. Pick

**Implement lane**, in `ROADMAP.md` table order: the first `ready` issue whose every dependency has
at least one `implemented` spec and no open issue carrying its name → run `/implement <issue>`.

**Spec lane**, in `ROADMAP.md` table order: the first `needs-spec` issue whose every dependency has
an `approved` or `implemented` spec → run `/spec <issue>`. Skip an issue whose title names the
capability the implement lane currently holds: its delta would be drafted against a spec that
PR is about to change.

Issues labeled `blocked` or `finding` are never picked. Issues that do not match a `ROADMAP.md`
capability (a change to an implemented capability, a promoted finding) have no dependencies and are
eligible on their label alone, after the roadmap capabilities.

Before picking, sweep open `finding` issues: relabel any with `Suggested triage: needs-spec` to
`needs-spec` (they become eligible for this same pick, in table order alongside the rest). Leave
`Suggested triage: human-judgment-needed` and unmarked findings untouched.

If nothing is eligible in this lane, say so in one line. If any open issue still carries `finding`
(i.e. `human-judgment-needed` or unmarked), list them with their `Suggested triage:` line (or "none
given" if missing) so a human can triage in one pass, then end. This is the expected outcome of
most unattended fires.

## 4. Run and end

Invoke the chosen skill for exactly that issue and end when it ends. Do not pick a second issue in
this session, in either lane, even if the first one finished quickly.
