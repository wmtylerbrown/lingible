import { Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';

/**
 * A system-defined Bedrock cross-region inference profile routes an `InvokeModel` request to a
 * fixed, AWS-defined set of underlying foundation-model regions. `bedrock:InvokeModel` must be
 * granted on the profile's own ARN *and* on the foundation-model ARN in every region the profile
 * can route to — granting only the profile ARN still fails closed with `AccessDeniedException`
 * once a request actually routes to one of those regions.
 *
 * Confirmed via `aws bedrock list-inference-profiles --region us-east-1` against the profile
 * family this codebase configures (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) on 2026-09-12:
 * the `us.` family's `models[].modelArn` list resolves to us-east-1/us-east-2/us-west-2. Re-verify
 * (and add an entry here) before pointing `llm.model` at a different profile family (e.g. `eu.` or
 * `global.`) — this map is not a general Bedrock routing reference.
 */
const CROSS_REGION_PROFILE_ROUTES: Readonly<Record<string, readonly string[]>> = {
  us: ['us-east-1', 'us-east-2', 'us-west-2'],
};

/**
 * Builds the `resources` list for a `bedrock:InvokeModel` IAM policy statement covering
 * `modelId` — either a plain foundation-model ID (always `anthropic.<...>`, e.g.
 * `anthropic.claude-3-haiku-20240307-v1:0`) or a cross-region inference-profile ID (a routing
 * prefix followed by a foundation-model ID, e.g. `us.anthropic.claude-haiku-4-5-20251001-v1:0`).
 *
 * For a plain foundation-model ID this returns a single foundation-model ARN in `region`. For a
 * known inference-profile family (see `CROSS_REGION_PROFILE_ROUTES`) it returns the profile's own
 * ARN (account-scoped, `/`-separated resource) plus the underlying foundation-model ARN in every
 * region the profile routes to.
 *
 * Throws for an inference-profile prefix this helper has no confirmed routing table for, rather
 * than silently granting a single-region ARN that would under-grant the real profile and leave
 * the Lambda failing closed with `AccessDeniedException` once AWS routes a request elsewhere —
 * add the family's routing table here (confirmed via `aws bedrock list-inference-profiles`) before
 * configuring `llm.model` to use it.
 */
export function getBedrockInvokeModelResources(scope: Construct, region: string, modelId: string): string[] {
  if (modelId.startsWith('anthropic.')) {
    return [`arn:aws:bedrock:${region}::foundation-model/${modelId}`];
  }

  const prefix = modelId.split('.')[0];
  const routes = CROSS_REGION_PROFILE_ROUTES[prefix];

  if (!routes) {
    throw new Error(
      `getBedrockInvokeModelResources: no confirmed cross-region routing table for inference-profile prefix "${prefix}." (model "${modelId}"). Add an entry to CROSS_REGION_PROFILE_ROUTES in backend/cdk/src/components/bedrock/invoke-model-resources.ts, confirmed via \`aws bedrock list-inference-profiles\`, before configuring llm.model to use this profile family.`
    );
  }

  const account = Stack.of(scope).account;
  const baseModelId = modelId.slice(prefix.length + 1);

  return [
    `arn:aws:bedrock:${region}:${account}:inference-profile/${modelId}`,
    ...routes.map((r) => `arn:aws:bedrock:${r}::foundation-model/${baseModelId}`),
  ];
}
