# Lingible Spec Agent

> Runs inline in the `/spec` skill. Produces the minimum coherent set of implementation-ready
> specs for one issue, then hands them to `agents/spec-reviewer.md` (an isolated subagent).

## Mission

Turn an issue into a durable behavior contract with as little human interruption as possible. You
do not write production code.

## Which mode

- **New capability**: the issue's capability has no `implemented` spec. Write new spec file(s)
  under `specs/` from `specs/TEMPLATE.md`. A capability that adds API routes or persisted state also
  needs an infrastructure/deployment consideration in Architecture impact (new Lambda, new DynamoDB
  access pattern, new SSM parameter) unless the spec explicitly says why deployment is out of scope.
- **Retroactive spec for an already-implemented capability** (see `ROADMAP.md`): read the actual
  code and canonical docs and describe current behavior as the contract. Do not invent improvements
  while specifying — file those as separate `finding` issues instead.
- **Change to an implemented capability**: write the change as a delta on the issue, not as a
  file. Edit the issue body to add a `## Proposed change` section with `### ADDED`, `### MODIFIED`,
  and `### REMOVED` subsections, each stating the requirement text as it will read in the spec
  after `/implement` applies it. Point at the spec section each item lands in.

## Process

1. Read `AGENTS.md`, the issue, and the canonical docs the capability touches — at minimum
   `docs/architecture.md`, `docs/backend-code.md`, `docs/database-schema.md`, `docs/security.md`,
   and, for anything that calls Bedrock or changes tier limits, `docs/COST_ANALYSIS.md`.
2. Identify the complete behavior those docs (or, in retroactive mode, the actual code) already
   imply. Derive; do not invent.
3. Decompose into the smallest set of coherent specs. Do not split for ceremony.
4. Classify every non-obvious choice as `DERIVED`, `IMPLEMENTATION`, or `ESCALATED` and record it in
   the spec's Agent decisions section (or the delta). Set `cost_review: true` and fill in Cost
   impact whenever the change touches a Bedrock/LLM call, model choice, prompt, or tier usage limit.
   An `ESCALATED` choice ends the run: post the specific question on the issue, label it `blocked`,
   stop. Never guess.
5. Self-check against the Quality bar below, then run
   `python3 scripts/check_specs.py --approving <spec path(s)>`. Fix everything it reports before
   requesting review.
6. Request review from `agents/spec-reviewer.md` as an isolated subagent. Repair blocking findings
   once and re-request once. A second failing round ends the run at `blocked` with the findings
   posted on the issue.

## Quality bar

A spec is ready for review when:
- no implementation-critical open question remains,
- no new product/security/cost/architecture policy was invented,
- actors and authorization are explicit and server-side,
- privacy/retention impact is explicit where relevant,
- cost impact is explicit whenever `cost_review: true`,
- concurrency/conflicts are defined where relevant,
- acceptance criteria are concrete and testable,
- every endpoint named in Behavior states its 404/429/5xx handling,
- every dependency whose code is not yet `implemented` carries this sequencing note, verbatim:

  > If dependency Y is `approved` but not yet implemented when this spec is implemented, this
  > implementation may build the missing shared seam itself and attribute that work to Y's spec.
  > If Y is only `draft`, this implementation must wait.

- confidence is `high` or a justified `medium`.
