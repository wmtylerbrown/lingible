---
name: pipeline
description: Do the next unit of pipeline work. The spec lane picks the next eligible `needs-spec` issue and runs /spec (single-flight). The implement lane picks every eligible `ready` issue whose expected scope doesn't overlap an already-active implement claim and launches /implement for each as a background subagent in its own worktree. Sweeps `finding` issues for mechanical needs-spec relabels first. Exits cheaply if a lane is busy or nothing is eligible. Use whenever the user says "keep the pipeline moving", "do the next thing", "work the queue", names /pipeline, or wraps it in /loop for unattended operation.
---

# pipeline

One pass per invocation: sweep findings, then launch whatever work is eligible right now, then end.
Never wait synchronously for a launched run to finish — that's what makes this safe to wrap in
`/loop /pipeline` for self-pacing, and what lets the implement lane run more than one issue at once.

Argument: `implement` or `spec`, naming the lane. With no argument, do both lanes in the same
invocation — they're independent and neither waits on the other.

## 1. Orient

`git fetch origin main` and read `ROADMAP.md` from `origin/main` (the capability table and its
"Depends on" column). List open issues with the GitHub tools available to this session.

## 2. Findings sweep (both lanes, always first)

Relabel any open `finding` issue whose latest `Suggested triage:` line says `needs-spec` to
`needs-spec` — that suggestion is itself the judgment call already made explicit in the issue's own
text, so acting on it needs no further review. It becomes eligible for step 4 like any other
`needs-spec` issue. Leave `Suggested triage: human-judgment-needed` and unmarked findings alone.

## 3. Lane check

**Spec lane** (single-flight): if any open issue carries `in-progress:spec`, read its
`Pipeline claimed <timestamp>` comment. Under three hours old, or an open PR references the issue →
the lane is busy, skip step 4 for spec this invocation. Otherwise the claim is stale: remove the
label, restore `needs-spec`, and treat the lane as free.

**Implement lane** (multi-flight): collect every open issue currently carrying
`in-progress:implement`. For each, read its claim comment and its `Expected scope:` line. A claim
older than three hours with no open PR referencing its issue is stale — remove the label, restore
`ready`, and drop it from the active set. What's left is the set of active claims this invocation
must not overlap.

## 4. Pick and launch

**Spec lane**, only if free: in `ROADMAP.md` table order, the first `needs-spec` issue whose every
dependency has an `approved` or `implemented` spec. Skip an issue whose title names the capability
an active implement claim is touching — its delta would be drafted against a spec that run is about
to change. If found: claim it (`in-progress:spec` + `Pipeline claimed <timestamp>` comment — no
scope needed, this lane is single-flight) and launch `/spec <issue>` via the `Agent` tool with
`isolation: "worktree"`, running in the background.

**Implement lane**: in `ROADMAP.md` table order, every `ready` issue whose every dependency has at
least one `implemented` spec and no open issue carrying its name, considered in order:
- Estimate its expected scope (the files/dirs its own description points at, or the capability's
  usual area from `ROADMAP.md`).
- Compare against every active claim's expected scope (the ones from step 3, plus any launched
  earlier in this same step). Any overlap, even partial → do not launch it this invocation; leave
  it for a later tick.
- No overlap → claim it (`in-progress:implement` + `Pipeline claimed <timestamp>. Expected scope:
  <paths>`) and launch `/implement <issue>` via the `Agent` tool with `isolation: "worktree"`,
  running in the background. Add it to the active-claims set before considering the next issue.

Issues labeled `blocked` or `finding` are never picked. Issues that don't match a `ROADMAP.md`
capability (a change to an implemented capability, a promoted finding) have no dependencies and are
eligible on their label alone, after the roadmap capabilities.

If a lane launched nothing, say why in one line (busy, nothing eligible, or everything eligible
overlapped an active claim). If any open issue still carries `finding` (`human-judgment-needed` or
unmarked), list it with its `Suggested triage:` line (or "none given") so a human can triage it.

## 5. End

Report what was launched (issue → subagent) and end immediately — do not wait for any launched run
to finish. Once real work is running, confirm the overlap assumption once each worktree exists:
`git status` / `git diff --stat` across the active implement worktrees should still show disjoint
files. If a later tick finds two active claims whose actual diffs overlap after all, that's a
correctness bug in the scope estimate, not something to paper over — flag it and let one of the two
runs continue while the other pauses for a human look.
