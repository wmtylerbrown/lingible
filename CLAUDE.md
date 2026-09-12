# Claude Code Adapter

Read and follow `AGENTS.md`. The workflow is `docs/development/AGENT_PROTOCOL.md`; the portable
role files are in `agents/`; the skills are `/spec`, `/implement`, `/pipeline`, and `/deploy` under
`.claude/skills/`.

## Subagents

`agents/spec-reviewer.md` and `agents/code-reviewer.md` must run as fresh-context subagents, never
inline. They are registered as Claude Code subagents in `.claude/agents/` under the same names, so
invoke them with the `Agent` tool by `subagent_type` (`spec-reviewer`, `code-reviewer`) and relay
the verdict back rather than folding the review into this session's reasoning. This is standing
instruction for the repository. `agents/spec-agent.md` and implementation run inline.

## Notifications

`AGENT_PROTOCOL.md` "Notify a human" names when to notify without naming a mechanism. In Claude Code
the mechanism is the `PushNotification` tool: one message under 200 characters leading with what
the human would act on (the issue and the blocker, or the PR and why it is waiting). Do not notify
on a routine autonomous completion.

## GitHub

Use the `gh` CLI for issues, labels, PRs, and merges. The `.claude/hooks/block-push-to-main.sh`
hook refuses any `git push` targeting `main`; every change is a PR.

## Deploys are separate from this pipeline

CI validates; it does not deploy. Deploys to dev/staging/prod are a human-initiated, single-person
action, run either directly (`npm run deploy:dev` / `npm run deploy:prod` in `backend/cdk/`) or via
the `/deploy` skill under `.claude/skills/` — never something `/pipeline`, `/implement`, `/spec`, or
any unattended routine reaches on its own. `/deploy` only ever runs from an explicit, same-turn
human invocation in an interactive session, and confirms the target and (for prod) the changeset
before executing. See `docs/development/AGENT_PROTOCOL.md` "Deploys stay separate from CI".

The repository, not this adapter or conversation memory, is the source of truth.
