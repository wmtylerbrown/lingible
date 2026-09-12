# Lingible API Cost Analysis

> **Current as of September 2026** (post [issue #9](https://github.com/wmtylerbrown/lingible/issues/9),
> the Bedrock model upgrade off Claude 3 Haiku). See "Current Cost Analysis" below for the live
> numbers — real token counts measured against the actual production prompts, the actual live
> tier limits, and `anthropic.claude-haiku-4-5-20251001-v1:0` (via the `us.` cross-region inference
> profile). The "Historical: January 2024 Analysis" section further down is kept for the cost
> *shape* and methodology it still illustrates (Bedrock dominates; API Gateway and Lambda are
> noise by comparison) — its dollar figures are superseded and should not be used.

## Overview

This document provides a comprehensive cost analysis for the Lingible API: AWS service costs, user
tier analysis, and business implications, recomputed against the live prompts, live tier limits,
and current Bedrock model (see "Current Cost Analysis" below).

## Current Cost Analysis (Post Bedrock Model Upgrade — September 2026)

Recomputed for [issue #9](https://github.com/wmtylerbrown/lingible/issues/9) against the actual
production prompt-building code (`SlangLLMService._create_genz_to_english_prompt`,
`_create_english_to_genz_prompt`, `SlangValidationService._create_validation_prompt`), the current
live tier limits, and real Bedrock token usage — not estimated token counts. Token figures below
are measured `usage.input_tokens`/`usage.output_tokens` from real `bedrock-runtime invoke-model`
calls against `us.anthropic.claude-haiku-4-5-20251001-v1:0` in `us-east-1`, run against
representative request text for each code path.

### Bedrock pricing used

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|---|---|---|
| Claude 3 Haiku (previous) | $0.25 | $1.25 |
| Claude Haiku 4.5 (current) | $1.00 | $5.00 |

Haiku 4.5 pricing confirmed against `claude.com/pricing` (Anthropic's Bedrock pricing matches its
first-party API pricing for this model) on 2026-09-12 — a 4x increase over Claude 3 Haiku on both
axes, matching the spec's cross-checked estimate.

### Measured token counts per request

| Code path | Case | Input tokens | Output tokens |
|---|---|---|---|
| GenZ→English translation | Free tier (≤50 chars), no lexicon match | 472 | 41 |
| GenZ→English translation | Free tier (≤50 chars), with lexicon term mapping | 630 | 52 |
| GenZ→English translation | Premium tier (≤100 chars), no lexicon match | 493 | ~43 |
| GenZ→English translation | Premium tier (≤100 chars), with lexicon term mapping | 658 | 78 |
| English→GenZ translation | Free tier (≤50 chars) | 350 | 52 |
| English→GenZ translation | Premium tier (≤100 chars) | 378 | ~45 |
| Slang-submission validation | No web search results | 347 | — |
| Slang-submission validation | With 2 web search results | 500 | 192 |
| Trending-terms generation (daily job) | Fixed prompt, 15–20 generated terms | 322 | 2,710 |

GenZ→English costs more per request than English→GenZ because its prompt carries the fuller rules
block, confidence-guideline coaching, and (when the lexicon matches) a term→gloss JSON block; a
lexicon match adds ~150-280 input tokens and ~10-25 output tokens versus no match. These are the
actual per-request drivers behind the cost table below, using the worst-case (lexicon-match)
GenZ→English figures as the conservative per-translation estimate.

### Free and premium tier monthly cost (heavy user, 30-day month)

Live limits: 10 translations/day free (50-char max), 100 translations/day premium (100-char max).

| Tier | Monthly translations | Conservative tokens/translation (in/out) | Claude 3 Haiku cost/month | Claude Haiku 4.5 cost/month |
|---|---|---|---|---|
| Free (heavy) | 300 | 630 / 52 | $0.07 | $0.27 |
| Premium (heavy) | 3,000 | 658 / 78 | $0.79 | $3.14 |

Using the lighter, no-lexicon-match case instead (472/41 free, 493/43 premium) — plausibly the more
common case given partial lexicon coverage — gives $0.20/month (free) and $2.12/month (premium) on
Haiku 4.5, close to the spec's pre-implementation estimate of $0.20/$2.03.

**Premium-tier heavy-user cost against $9.99/month subscription revenue: $2.12–$3.14/month on
Claude Haiku 4.5, still comfortably under 32% of revenue even in the conservative case** — a real,
roughly 4x increase in per-request Bedrock cost, but not a threat to unit economics at current tier
limits. This confirms the spec's Cost impact analysis: the tier limits were cut ~100x since Claude
3 Haiku was chosen, leaving large unused cost headroom regardless of which current-generation
Haiku-tier model is picked.

### Slang validation and trending-job cost

These run at much lower volume than translation (validation only on new slang submissions;
trending generation once/day) and were not previously included in the free/premium unit-economics
comparison above, but are included here for completeness:

- **Slang validation** (with web search results, the more expensive case — 500 in / 192 out):
  ~$0.0015/submission on Haiku 4.5 (~$0.0004 on Claude 3 Haiku). At realistic submission volumes
  (tens to low hundreds/month), this is noise relative to translation volume.
- **Trending-terms generation** (322 in / 2,710 out, once/day): ~$0.0139/run on Haiku 4.5
  (~$0.0035/run on Claude 3 Haiku) → ~$0.42/month on Haiku 4.5 (~$0.10/month on Claude 3 Haiku) for
  the daily scheduled job. Larger relative increase than translation because this path is almost
  all output tokens, and output is the more expensive side of the 4x price increase, but the
  absolute dollar amount stays small.

### Conclusion

The model upgrade is affordable at current tier limits and volume. Bedrock remains ~90%+ of
per-request cost (see the historical section below for why that's structural, not model-specific);
this change shifts that cost up roughly 4x per token without threatening premium-tier margin. No
change to tier limits is warranted by this analysis alone.

## Historical: January 2024 Analysis (superseded by "Current Cost Analysis" above)

Kept for the cost *shape* and methodology it illustrates (Bedrock dominates; API Gateway and
Lambda are noise by comparison) — every dollar figure below is superseded by the real-prompt,
real-tier-limit numbers above and should not be used for a current decision.

## AWS Service Pricing (as of January 2024 — re-check current Bedrock pricing before relying on this)

### AWS Bedrock (Claude 3 Haiku)
- **Input tokens**: $0.25 per 1M tokens
- **Output tokens**: $1.25 per 1M tokens
- **Token-to-character ratio**: ~4 characters per token

### API Gateway
- **Requests**: $3.50 per 1M requests
- **Data transfer**: $0.09 per GB

### AWS Lambda
- **Requests**: $0.20 per 1M requests
- **Duration**: $0.0000166667 per GB-second

## Tier Limits Assumed By This Analysis (OUTDATED — see current values below)

### Free Tier (as analyzed here)
- **Daily Characters**: 5,000 characters
- **Daily Translations**: 50 requests
- **Daily Trending Requests**: 100 requests
- **Max Text Length**: 100 characters per request

### Premium Tier (as analyzed here)
- **Daily Characters**: 100,000 characters
- **Daily Translations**: 10,000 requests
- **Daily Trending Requests**: 10,000 requests
- **Max Text Length**: 500 characters per request
- **Monthly Price**: $9.99

### Current live limits (`shared/config/backend/{dev,prod}.json`, both environments — checked at restore time)
- **Free**: 10 daily translations, 50-character max text length
- **Premium**: 100 daily translations, 100-character max text length
- These are far lower than what this analysis assumed, which mechanically lowers the per-user
  cost estimates below — but the current translation prompt is also longer (it includes lexicon
  term→gloss context, casual-tone coaching, and worked examples), which raises per-request token
  cost. The two effects don't cancel out predictably; this needs a real recompute, not a scaling
  factor applied to the numbers below.

## Cost Calculation Methodology

### Bedrock Prompt Analysis (the prompt this analysis assumed — NOT the current one)

**System prompt this analysis was based on:**
```
You are a helpful AI assistant that decodes teen slang and Gen Z language to standard {target_language}.

Please decode the following slang text to standard {target_language}.

Slang text to decode: "{text}"

{f"Context: {context}" if context else ""}

Please provide only the decoded text, nothing else. Keep the translation natural and contextually appropriate for the specified mode.

Decoded text:
```

**Token Count Breakdown:**
- **System prompt**: ~50 tokens (base prompt without user text)
- **User text**: 100 characters ÷ 4 = 25 tokens
- **Total input tokens**: ~75 tokens per request
- **Output tokens**: ~75 × 1.5 = 112.5 tokens (estimated)

The live prompt (`SlangLLMService._create_genz_to_english_prompt`) is substantially longer than
this — it carries the full rules block, confidence-guideline coaching, six worked examples, and
(when the lexicon matches terms) a JSON block of term→gloss mappings. Estimate its real token
count from the actual rendered string, not from this 50-token figure.

## Free Tier Cost Analysis (using this analysis's assumed limits, not current ones)

### Daily Usage (5,000 characters, 50 translations)

#### Bedrock Costs
- **Input tokens per translation**: 75 tokens
- **Output tokens per translation**: 112.5 tokens
- **Daily input tokens**: 75 × 50 = 3,750 tokens
- **Daily output tokens**: 112.5 × 50 = 5,625 tokens
- **Daily input cost**: (3,750 ÷ 1,000,000) × $0.25 = **$0.0009375**
- **Daily output cost**: (5,625 ÷ 1,000,000) × $1.25 = **$0.00703125**
- **Total daily Bedrock cost**: **$0.00796875**

#### API Gateway Costs
- **Daily requests**: 50 translations
- **Daily API Gateway cost**: (50 ÷ 1,000,000) × $3.50 = **$0.000175**

#### Lambda Costs
- **Daily Lambda requests**: 50 translations
- **Daily Lambda request cost**: (50 ÷ 1,000,000) × $0.20 = **$0.00001**
- **Lambda duration**: Assuming 2 seconds per request, 512MB memory
- **Daily Lambda duration cost**: 50 × 2 × 0.5 × $0.0000166667 = **$0.000833**

#### Total Daily Cost
- **Bedrock**: $0.00796875
- **API Gateway**: $0.000175
- **Lambda**: $0.000843
- **Total**: **$0.00898675 per day**

### Monthly Cost Estimates

| Usage Level | Daily Cost | Monthly Cost | Annual Cost |
|-------------|------------|--------------|-------------|
| Heavy User (100%) | $0.00898675 | $0.27 | $3.24 |
| Moderate User (50%) | $0.004493 | $0.135 | $1.62 |
| Light User (25%) | $0.002247 | $0.067 | $0.80 |

### Cost Breakdown by Service

| Service | Daily Cost | Percentage |
|---------|------------|------------|
| Bedrock | $0.00796875 | 89% |
| Lambda | $0.000843 | 9% |
| API Gateway | $0.000175 | 2% |

**This is the durable takeaway even though the dollar figures are stale: Bedrock is ~90% of
per-request cost, API Gateway and Lambda are rounding errors. Any cost-reduction effort should
aim at Bedrock (model choice, prompt length, call volume), not infrastructure.**

## Premium Tier Cost Analysis (using this analysis's assumed limits, not current ones)

### Daily Usage (100,000 characters, 10,000 translations)

#### Bedrock Costs
- **Input tokens per translation**: 125 tokens (500 chars ÷ 4)
- **Output tokens per translation**: 187.5 tokens
- **Daily input tokens**: 125 × 10,000 = 1,250,000 tokens
- **Daily output tokens**: 187.5 × 10,000 = 1,875,000 tokens
- **Daily input cost**: (1,250,000 ÷ 1,000,000) × $0.25 = **$0.3125**
- **Daily output cost**: (1,875,000 ÷ 1,000,000) × $1.25 = **$2.34375**
- **Total daily Bedrock cost**: **$2.65625**

#### API Gateway Costs
- **Daily requests**: 10,000 translations
- **Daily API Gateway cost**: (10,000 ÷ 1,000,000) × $3.50 = **$0.035**

#### Lambda Costs
- **Daily Lambda requests**: 10,000 translations
- **Daily Lambda request cost**: (10,000 ÷ 1,000,000) × $0.20 = **$0.002**
- **Lambda duration**: Assuming 2 seconds per request, 512MB memory
- **Daily Lambda duration cost**: 10,000 × 2 × 0.5 × $0.0000166667 = **$0.1667**

#### Total Daily Cost
- **Bedrock**: $2.65625
- **API Gateway**: $0.035
- **Lambda**: $0.1687
- **Total**: **$2.85995 per day**

### Monthly Cost Estimates

| Usage Level | Daily Cost | Monthly Cost | Annual Cost |
|-------------|------------|--------------|-------------|
| Heavy User (100%) | $2.85995 | $85.80 | $1,029.60 |
| Moderate User (50%) | $1.42998 | $42.90 | $514.80 |
| Light User (25%) | $0.71499 | $21.45 | $257.40 |

*(Against this analysis's assumed 10,000-translation/day premium ceiling — the live premium
ceiling is 100 translations/day, two orders of magnitude lower, so the real current worst-case
premium-user cost is far below this. Still needs recomputing against the real prompt and limits.)*

## Business Model Analysis (directional — recompute against current limits before trusting the dollar amounts)

### Revenue vs Cost Comparison (as analyzed here, not current)

#### Free Tier
- **Revenue**: $0/month
- **Cost (Heavy User)**: $0.27/month
- **Net Loss**: $0.27/month per heavy user

#### Premium Tier
- **Revenue**: $9.99/month
- **Cost (Heavy User)**: $85.80/month
- **Net Loss**: $75.81/month per heavy user

*(This "premium loses money on heavy use" conclusion was a live concern in Jan 2024, and looks
like exactly why the premium daily-translation ceiling dropped from 10,000 to 100 since then —
worth confirming that reasoning explicitly once the numbers are recomputed, rather than assuming.)*

### Key Insights (still worth checking, not still worth trusting the numbers behind them)

1. **Free Tier Sustainability**: Even heavy users cost only cents/year at these token counts, making the free tier cheap to sustain — recheck against the real prompt length.
2. **Premium Tier Challenge**: A high enough per-user ceiling can make heavy premium users cost more than the subscription price — this is presumably why the ceiling was cut; confirm.
3. **Usage Optimization**: The business model relies on most users being light/moderate users.
4. **Scale Benefits**: Costs decrease per user with volume due to AWS pricing tiers.

### Risk Mitigation Strategies (still relevant as a checklist, independent of the stale numbers)

#### 1. Usage Monitoring
- Real-time usage tracking (the current tier system already enforces daily limits server-side).
- Alerts for high-usage users / cost anomalies (no CloudWatch cost alarms currently exist — see [issue #9](https://github.com/wmtylerbrown/lingible/issues/9)).

#### 2. Cost Optimization
- **Prompt Engineering**: Reduce system prompt length — directly relevant to [issue #9](https://github.com/wmtylerbrown/lingible/issues/9) and [issue #10](https://github.com/wmtylerbrown/lingible/issues/10) (whether the lexicon hybrid still earns its cost).
- **Caching**: Cache common slang translations.
- **Model Selection**: done — [issue #9](https://github.com/wmtylerbrown/lingible/issues/9) moved translation/validation off Claude 3 Haiku to Claude Haiku 4.5 (see "Current Cost Analysis" above). Prompt simplification (a stronger model may need less scaffolding) was explicitly deferred as a follow-up requiring its own quality evaluation, not bundled into that change.

#### 3. Pricing Strategy
- **Usage-based Pricing**: Charge per translation beyond limits.
- **Tiered Premium**: Multiple premium tiers with different limits.

## Recommendations

### Immediate
- Done: this document is recomputed against the live prompt, live tier limits, and current Bedrock model/pricing (see "Current Cost Analysis" above; [issue #9](https://github.com/wmtylerbrown/lingible/issues/9)).
- Set up CloudWatch cost alarms/budgets for Bedrock spend — none currently exist.

### Short-term
- Decide, with real numbers, whether the lexicon-matching step is still earning its engineering cost relative to a pure-LLM approach on a stronger model ([issue #10](https://github.com/wmtylerbrown/lingible/issues/10)).

### Ongoing
- Keep this document current: any change to the LLM model, the translation/validation prompts, or
  the tier limits should update the relevant numbers above in the same PR, or add a row to "Recent
  changes reviewed" below stating there is none and why. `scripts/check_bedrock_cost_review.py`
  enforces the mechanical half of this: it fails CI whenever a Bedrock-cost-relevant file changes
  without this document changing too (see `docs/development/AGENT_PROTOCOL.md` — cost impact is
  also a required spec/review consideration for LLM-touching changes).

## Recent changes reviewed

When a change to a Bedrock-cost-relevant file (the LLM call sites, `LLMConfig`, or the
`llm`/`limits` blocks in `shared/config/backend/{dev,prod}.json`) genuinely has no cost impact (a
pure refactor, a type-hint fix, a log-line tweak), add one line here instead of a full recompute —
that's what satisfies `scripts/check_bedrock_cost_review.py` and what makes this list itself a real
record that a human or agent actually looked, not just an assumption.

| Date | Change | Cost impact |
|---|---|---|
| 2026-09-12 | `llm.model` changed from `anthropic.claude-3-haiku-20240307-v1:0` to `us.anthropic.claude-haiku-4-5-20251001-v1:0` ([issue #9](https://github.com/wmtylerbrown/lingible/issues/9)) | Full recompute above: ~4x per-token cost increase, heavy-user premium cost rises from ~$0.79/month to ~$2.12–$3.14/month against $9.99 revenue — affordable at current tier limits, not a threat to unit economics. |
| 2026-09-12 | `backend/lambda/src/services/slang_validation_service.py` reformatted by `ruff format` as part of the Poetry→uv/ruff/nox toolchain migration ([issue #12](https://github.com/wmtylerbrown/lingible/issues/12)) | No cost impact: purely mechanical (one string literal's quote style, `'Not provided'` → `"Not provided"`), content-identical — no change to the prompt text, token count, model, or call volume. |

---

*Originally written: January 2024, against Claude 3 Haiku and the tier limits stated in the historical section above.*
*Restored to `main` and annotated: September 2026, after being dropped during the November 2025 repo reorganization.*
*Recomputed with real measured token counts against the live prompt, live tier limits, and Claude Haiku 4.5: September 2026 ([issue #9](https://github.com/wmtylerbrown/lingible/issues/9)). See "Current Cost Analysis" above.*
