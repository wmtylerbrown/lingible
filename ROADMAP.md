# Lingible Capability Roadmap

The capabilities that make up Lingible and the order they build in. Nothing else.

- **Queue state** (what needs a spec, what is ready, what is claimed, what is blocked) lives in
  GitHub Issues, one issue per capability or change, labeled per
  `docs/development/AGENT_PROTOCOL.md` "Issues are the queue".
- **Spec state** (`draft`, `approved`, `implemented`, `retired`) lives in each spec's front matter.
- A capability with no spec listed has not been specified yet — everything below predates this
  pipeline, so every row starts with an empty Specs column even though the capability is already
  built and live. Writing a spec for an already-implemented capability means describing its actual
  current behavior (mode: retroactive), not proposing new behavior.
- Changing an implemented capability does not add a row here: it is an issue plus an in-place edit
  of the existing spec, once one exists.

## Capabilities

| Capability | Specs | Depends on |
|---|---|---|
| Auth & identity (Cognito, Apple Sign-In) | — | — |
| Infrastructure & deployment (CDK: Shared/Data/Async/Api/Website stacks) | — | — |
| Translation (GenZ ↔ English, lexicon + Bedrock hybrid) | — | Auth & identity, Infrastructure & deployment |
| Trending terms | — | Translation |
| Slang crowdsourcing & AI validation | — | Translation, Auth & identity |
| Quiz / gamification | — | Slang crowdsourcing & AI validation |
| Subscriptions & billing (StoreKit 2, App Store receipt validation) | — | Auth & identity |
| Marketing website & legal pages | — | Infrastructure & deployment |
| iOS app | — | Auth & identity, Translation, Trending terms, Quiz / gamification, Slang crowdsourcing & AI validation, Subscriptions & billing |

## Notes for the first specs written against this roadmap

- Because every capability above is already implemented, the first spec for each will typically be
  written in **retroactive mode**: read the actual code (`backend/lambda/src/services/`,
  `backend/lambda/src/handlers/`, `backend/cdk/`, `ios/`) and canonical docs (`docs/architecture.md`,
  `docs/backend-code.md`, `docs/database-schema.md`, `docs/security.md`, `docs/COST_ANALYSIS.md`)
  and describe what actually exists, rather than deriving new behavior from product docs that don't
  fully exist yet. Flag anywhere the code and this roadmap's assumed dependency order disagree.
- Update this table's dependency edges as real specs reveal the actual coupling — the edges above
  are a first-pass approximation from reading the code, not yet spec-verified.
