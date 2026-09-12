# Lingible API Cost Analysis

> **⚠️ STALE — needs a refresh.** This analysis was written in January 2024 against a much
> shorter translation prompt and different tier limits than what's live today. It was lost from
> `main` during the November 2025 repo reorganization and is restored here as a starting point,
> not a current number. See [issue #9](https://github.com/wmtylerbrown/lingible/issues/9), which
> now includes recomputing this doc against the actual current prompt
> (`SlangLLMService._create_genz_to_english_prompt`, materially longer than the prompt this
> analysis assumed), the actual current tier limits (`shared/config/backend/{dev,prod}.json`,
> which differ from the limits below), and whichever Bedrock model that investigation lands on.
> Do not use the dollar figures below for a current decision — use them only to understand the
> cost *shape* (Bedrock dominates; API Gateway and Lambda are noise by comparison) and the
> methodology, both of which still hold.

## Overview

This document provides a comprehensive cost analysis for the Lingible API, including AWS service costs, user tier analysis, and business implications. The analysis is based on tier limits and AWS pricing as of January 2024.

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
- **Model Selection**: A current-generation model may need less prompt scaffolding to hit the same quality bar, which is itself a token-cost reduction — part of [issue #9](https://github.com/wmtylerbrown/lingible/issues/9).

#### 3. Pricing Strategy
- **Usage-based Pricing**: Charge per translation beyond limits.
- **Tiered Premium**: Multiple premium tiers with different limits.

## Recommendations

### Immediate
- Recompute this entire document against the live prompt, live tier limits, and current Bedrock pricing (tracked in [issue #9](https://github.com/wmtylerbrown/lingible/issues/9)).
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

---

*Originally written: January 2024, against Claude 3 Haiku and the tier limits stated above.*
*Restored to `main` and annotated: September 2026, after being dropped during the November 2025 repo reorganization. Dollar figures not yet re-verified against current prompt/limits/pricing.*
