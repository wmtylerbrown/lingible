---
id: SPEC-XXX
title: Short feature name
status: draft  # draft | approved | implemented | retired
approval: autonomous  # autonomous | human_required
confidence: high  # low | medium | high
risk: low  # low | medium | high
capability: Capability name from ROADMAP.md
issue: null  # GitHub issue number this spec was drafted for
security_review: false
security_domains: []  # auth | authorization | pii | retention | token | iam | external_service | payments
cost_review: false  # true if this spec adds/changes a Bedrock (or other metered LLM) call, model, prompt, or tier limit
affected_docs: []
derived_decisions: 0
implementation_decisions: 0
escalated_decisions: 0
security_test_ref: null  # repo path to the executed security tests; required at 'implemented' when security_review: true
---

# Feature title

## Intent

Why this feature exists and what user outcome it enables.

## Existing decisions

List the canonical product/domain/security/cost decisions that already govern this feature.
Do **not** restate whole documents; capture only what directly constrains this feature.

## Behavior

Describe the required behavior in precise, implementation-independent language. Every endpoint
named here states its 404/429/5xx handling.

## Actors and authorization

Who may perform each action, and what current server-side state establishes that authority.

## Privacy and data classification

Identify any PII read or written, visibility rules, retention impact, and
notification/logging constraints.

## Cost impact

Only required when `cost_review: true`. State: whether this touches a Bedrock (or other metered
LLM) call; the expected per-request token/cost delta versus current behavior; whether
`docs/COST_ANALYSIS.md` needs updating in the implementing PR; and whether the change could
materially raise per-user cost at a tier's usage ceiling. A cost increase that is not clearly
bounded and budgeted is an `ESCALATED` decision (see Agent decisions below), not an autonomous one.

If not applicable, say `None`.

## Acceptance criteria

Use concrete, testable scenarios. These should be strong enough that an implementation
agent does not need to invent product behavior.

## Failure and edge cases

Define important conflict, concurrency, invalid-state, and authorization behavior.

## Architecture impact

Only include what is necessary:
- API changes
- DynamoDB access-pattern/projection changes
- new infrastructure/dependencies
- meaningful module-boundary changes
- Bedrock/LLM usage changes (model, prompt, call volume) — cross-reference the Cost impact section

If none, say `None`.

## Documentation impact

List canonical docs that must change as a consequence of the implementation.
Do not create addendums; update the section that owns the rule.

## Agent decisions

Record only decisions made autonomously while specifying this feature.

Classify each as:
- `DERIVED` — directly implied by canonical docs.
- `IMPLEMENTATION` — reasonable technical choice within existing architecture.
- `ESCALATED` — new product/security/cost/architecture policy requiring human input.

## Open questions

Only genuine product/security/cost/architecture questions not answered by existing docs. Must be
empty before `status: approved`.
