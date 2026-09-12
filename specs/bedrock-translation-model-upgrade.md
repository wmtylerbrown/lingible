---
id: SPEC-TRANSLATE-MODEL-001
title: Upgrade the Bedrock translation/validation model off Claude 3 Haiku
status: approved
approval: human_required
confidence: medium
risk: medium
capability: Translation (GenZ ↔ English, lexicon + Bedrock hybrid)
issue: 9
security_review: true
security_domains: [iam]
cost_review: true
affected_docs: [docs/COST_ANALYSIS.md]
derived_decisions: 2
implementation_decisions: 4
escalated_decisions: 0
security_test_ref: null
---

# Upgrade the Bedrock translation/validation model off Claude 3 Haiku

## Intent

Dev and prod are both pinned to `anthropic.claude-3-haiku-20240307-v1:0` — Claude 3 Haiku, launched
March 2024 and now a legacy-generation model on Bedrock. This spec covers upgrading the model(s)
Lingible's LLM calls use, so translation and slang-validation quality benefit from a current
generation model, informed by an accurate current cost picture (the previous cost analysis was
computed against limits and a prompt that no longer reflect production).

This spec does **not** cover the lexicon-freshness/crowdsourcing-pipeline question (tracked
separately in #10) — that's a different problem (coverage of post-training-cutoff slang) that a
model upgrade does not solve.

## Existing decisions

- `docs/architecture.md`, `docs/backend-code.md`: model, prompt, and tier-limit configuration is
  entirely SSM/config-driven (`LLMConfig`, `shared/config/backend/{dev,prod}.json`) — no model ID
  or prompt text is hardcoded outside config and the prompt-building methods.
- `docs/COST_ANALYSIS.md` (restored/annotated in #11): Bedrock is consistently ~90% of Lingible's
  per-request cost; API Gateway and Lambda are noise by comparison. Live tier limits are 10
  translations/day (free, 50-char max text) and 100/day (premium, 100-char max text) —
  substantially lower than the 50/10,000-per-day limits the original 2024 cost analysis assumed.

## Behavior

No user-facing API behavior changes. This is a backend configuration and infrastructure change:

- `LLMConfig.model` (used by `SlangLLMService` for translation and `SlangValidationService` for
  slang-submission validation) changes from `anthropic.claude-3-haiku-20240307-v1:0` to a
  current-generation model.
- `trending_service.py`'s `_call_bedrock_for_trending_terms` also reads `self.llm_config.model`
  (the same config value), so the trending-generation job moves to the new model too, as a direct
  consequence rather than a separately decided change.
- Three Lambda functions call `invoke_model` against this config value:
  `translateLambda` (`api-construct.ts`), and `SlangValidationProcessor` and `TrendingJobLambda`
  (both `async-construct.ts`). All three need a working `bedrock:InvokeModel` grant for whatever
  ARN shape the chosen model/inference-profile actually requires — see Architecture impact. Per
  #14 (filed during this spec's research), `SlangValidationProcessor` and `TrendingJobLambda`
  currently appear to have **no** `bedrock:InvokeModel` grant at all, independent of which model is
  configured — this spec's implementation must resolve that as a precondition of moving those two
  functions to a new model, not just update `translateLambda`'s existing grant.
- No change to `max_tokens`, `temperature`, `top_p`, or the prompt text itself in this spec —
  prompt simplification (a stronger model may need less scaffolding) is called out as a candidate
  follow-up, not bundled into this change, since it needs its own quality evaluation.

## Actors and authorization

No change. This affects only server-side Bedrock invocation; no new actor or authorization surface.

## Privacy and data classification

No change to what data is sent to Bedrock (user-submitted translation text, already sent to the
current model). No new data classification introduced by a model swap within the same provider
(Anthropic via Bedrock).

## Cost impact

**Current, recomputed cost** (against the *actual* live prompt and live tier limits, not the stale
2024 assumptions):

- Live translation prompt (`SlangLLMService._create_genz_to_english_prompt`) is materially longer
  than the 2024 analysis assumed: rules block, confidence-guideline coaching, 6 worked examples,
  and (when lexicon terms match) a JSON term→gloss block. Estimated ~320–425 input tokens per
  request (vs. the old ~75-token assumption), plus live text is capped at 50 (free) / 100 (premium)
  characters (~12–25 tokens) — already included in that range. Output is a short JSON object
  (translated text + applied_terms + confidence), realistically well under the configured
  `max_tokens: 500` ceiling — estimated ~40–80 tokens for text this short.
- **On current model (Claude 3 Haiku, $0.25/$1.25 per 1M in/out)**: a heavy free user (10/day, 30
  days) costs roughly **$0.05/month**; a heavy premium user (100/day) costs roughly **$0.51/month**
  against $9.99 subscription revenue.

**Candidate model: Claude Haiku 4.5** (`anthropic.claude-haiku-4-5-20251001-v1:0` family, launched
Oct 2025, knowledge cutoff Feb 2025 — exact inference-profile ID form to be confirmed at
implementation time, see Acceptance criteria). Pricing, cross-checked via two independent research
passes (this spec's and the isolated spec-reviewer's): **$1.00 input / $5.00 output per 1M
tokens**, a 4x increase over Claude 3 Haiku on both axes. Recommend one final confirmation against
the AWS Bedrock console's own pricing view at implementation time as standard practice before
relying on it for the sign-off below, given AWS's own pricing page didn't render fully during
either research pass.

- Same heavy free user: roughly **$0.20/month**.
- Same heavy premium user: roughly **$2.03/month** against $9.99 revenue — still comfortably
  affordable, though no longer a rounding error.
- At current, very low tier limits, a 4x per-token cost increase does **not** threaten unit
  economics. This is the central finding that makes this change low-cost-risk: the tier limits
  were cut ~100x (10,000/day → 100/day for premium) since the model was last chosen, so there is
  large, currently-unused cost headroom regardless of which current-generation model is picked.
- `docs/COST_ANALYSIS.md` must be updated in the implementing PR with the actual post-switch
  numbers (real prompt token counts measured from production, not estimated), satisfying
  `scripts/check_bedrock_cost_review.py`.

A materially more expensive tier (e.g. Sonnet-class, roughly 8–20x Claude 3 Haiku's price per
several sources) would erode premium-tier margin far more meaningfully and is explicitly **not**
recommended by this spec without a separate, dedicated cost/quality justification.

## Acceptance criteria

- `shared/config/backend/dev.json` and `shared/config/backend/prod.json`'s `llm.model` value is
  updated to the chosen current-generation model ID (exact inference-profile string confirmed at
  implementation time against the deployed region — see Agent decisions).
- The IAM policy granting `bedrock:InvokeModel` to **all three** Bedrock-calling Lambdas —
  `translateLambda` (`api-construct.ts`), `SlangValidationProcessor`, and `TrendingJobLambda` (both
  `async-construct.ts`) — is updated/added to permit the new model/inference profile's actual
  resource ARN — **not** a no-op config change, and not scoped to `translateLambda` alone. Claude
  Haiku 4.5's Bedrock model card shows in-Region invocation is not supported for any AWS region;
  only Geo (e.g. `us.anthropic.claude-haiku-4-5-20251001-v1:0`) or Global
  (`global.anthropic.claude-haiku-4-5-20251001-v1:0`) cross-region inference profile IDs work for
  the `InvokeModel` API this codebase uses. An inference-profile ARN
  (`arn:aws:bedrock:{region}:{account}:inference-profile/{profile-id}`) is a different resource
  type than the current foundation-model ARN
  (`arn:aws:bedrock:{region}::foundation-model/{model}`) `translateLambda`'s statement grants today,
  and Bedrock cross-region inference profiles typically also require `bedrock:InvokeModel`
  permission on the underlying foundation-model ARN(s) in every region the profile can route to.
  `SlangValidationProcessor` and `TrendingJobLambda` need this grant added for the first time (see
  #14) — get any of the three wrong and that function's Bedrock call fails closed with
  `AccessDeniedException`.
- `SlangValidationService._call_claude` (unlike `SlangLLMService`'s translation methods) re-raises
  on exception rather than catching it — so a missing/incorrect IAM grant there is a **hard**
  failure of the async slang-validation pipeline, not a soft degrade. Implementation should confirm
  this Lambda's grant is correct before relying on the "fails soft" framing in Failure and edge
  cases below, which applies to translation, not validation.
- Bedrock model access for the chosen model is confirmed granted in both the dev and prod AWS
  accounts before deployment (Bedrock requires an explicit per-model access grant per account;
  access to Claude 3 Haiku does not imply access to Claude Haiku 4.5).
- Translation (`POST /translate`, both directions) and slang-submission validation continue to
  return well-formed responses against the new model in dev before promoting to prod.
- `docs/COST_ANALYSIS.md` is updated with real post-switch cost figures.

## Failure and edge cases

- **Missing model access or missing/incorrect IAM grant, translation path**: `invoke_model` raises
  `AccessDeniedException`. `SlangLLMService.translate_with_context` and `.translate_to_genz` already
  catch this in their existing `except Exception` fallback (returns a low-confidence fallback
  translation rather than a 5xx to the user) — so this fails soft for the end user, but silently
  from a monitoring standpoint.
- **Missing model access or missing/incorrect IAM grant, validation path**: unlike translation,
  `SlangValidationService._call_claude` re-raises rather than catching — the same failure here is a
  **hard** failure of the async slang-validation pipeline, not a soft degrade. This is the path most
  at risk given #14's finding that this Lambda currently has no working grant at all.
- **JSON-format non-compliance**: `_parse_llm_response`'s existing markdown/malformed-JSON cleanup
  logic stays as a defensive fallback; a materially more compliant model should reduce how often it
  triggers, not eliminate the need for it in this change.
- **Region/model unavailability**: if the account's deployed region doesn't support the chosen
  model directly, the Geo or Global inference profile handles routing — confirm the actual deployed
  region's support status before implementation (this spec does not have AWS account access to
  verify it directly; see Acceptance criteria).

## Architecture impact

- Config change: `shared/config/backend/{dev,prod}.json` `llm.model` value.
- **Infrastructure/IAM change** (not a config-only change, despite the change looking small):
  - `backend/cdk/src/constructs/api-construct.ts`'s IAM `PolicyStatement` for `translateLambda`
    needs its `resources` ARN updated from a `foundation-model` ARN to whatever ARN shape the
    chosen model/inference-profile actually requires.
  - `backend/cdk/src/constructs/async-construct.ts`'s `SlangValidationProcessor` and
    `TrendingJobLambda` need a `bedrock:InvokeModel` grant added for the same ARN — closing the gap
    #14 identified — since neither currently has one for any model.
  - This is why `security_review: true` / `security_domains: [iam]` are set above: this spec's
    core change is an IAM boundary change (foundation-model ARN → inference-profile ARN, a new
    grant on two Lambdas that had none), not merely a config value swap.
- No DynamoDB, API contract, or domain-event changes.

## Documentation impact

- `docs/COST_ANALYSIS.md`: updated with real post-switch cost figures (required by
  `scripts/check_bedrock_cost_review.py`).

## Agent decisions

- **DERIVED**: Bedrock is Lingible's dominant per-request cost (`docs/COST_ANALYSIS.md`), so any
  model choice must be justified against actual token/cost math, not assumed safe or assumed
  unaffordable.
- **DERIVED**: the live tier limits (10/day free, 100/day premium) are ~100x lower than the limits
  the original 2024 cost analysis assumed, which is why a materially pricier model is now
  affordable in a way it may not have been when Claude 3 Haiku was originally chosen.
- **IMPLEMENTATION**: recommending Claude Haiku 4.5 specifically (current-generation, same
  Haiku-tier latency/cost profile as today, no architectural changes needed beyond the IAM/model-ID
  update) rather than a Sonnet-class model, since the cost math strongly favors staying in the
  Haiku tier at current volume and there's no evidence yet that translation quality specifically
  needs Sonnet-level capability.
- **IMPLEMENTATION**: not bundling prompt simplification into this change, even though a stronger
  model plausibly needs less scaffolding — that's a quality/cost follow-up requiring its own
  evaluation, not something to decide blind alongside a model swap.
- **IMPLEMENTATION**: the exact model ID / inference-profile string to use in config depends on
  which AWS region(s) Lingible is actually deployed to (needed to pick between a `us.`/`eu.`/etc.
  Geo profile and the `global.` profile) — this spec's author does not have access to the live AWS
  account to confirm the deployed region. Not treated as a product/architecture policy question
  (there's no real choice to make once the region is known — the profile ID is mechanically
  determined by it), so it's a required implementation-time verification step (see Acceptance
  criteria), not an open design question.
- **IMPLEMENTATION**: whether Bedrock model access for the chosen model is already granted in the
  dev and prod AWS accounts, or needs to be requested first, is likewise a fact to verify at
  implementation time (this spec's author cannot check AWS account state directly), not a decision
  with more than one reasonable answer.

`approval: human_required` (rather than these two verification steps) is the mechanism carrying
this spec's actual caution: a real, if small, increase in ongoing AWS spend should get an explicit
human nod before the implementing PR merges, even though the cost math above supports it
comfortably. The $1.00/$5.00 Haiku 4.5 pricing used in Cost impact has been cross-checked via two
independent research passes (this spec's and the isolated spec-reviewer's, both via web search); a
routine final confirmation against the AWS Bedrock console's own pricing view at implementation
time is good practice before relying on it for that sign-off, consistent with the Cost impact
section above.

## Open questions

None.
