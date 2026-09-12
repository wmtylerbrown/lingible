/**
 * Standalone verification for `getBedrockInvokeModelResources` (src/components/bedrock/
 * invoke-model-resources.ts) -- the function that builds the `bedrock:InvokeModel` IAM
 * `resources` list for `translateLambda`, `SlangValidationProcessor`, and `TrendingJobLambda`
 * (issue #9). This is a plain script rather than a jest suite because the CDK package has no test
 * runner set up; it follows the same pattern as `scripts/check_specs.py` and
 * `scripts/check_bedrock_cost_review.py` at the repo root -- a small script wired into
 * `scripts/verify`, not a new testing framework.
 *
 * This exists because the resource ARNs are the actual security boundary here
 * (security_domains: [iam]): getting the inference-profile ARN or the cross-region
 * foundation-model ARNs wrong means `SlangValidationProcessor` and `TrendingJobLambda` -- which,
 * per issue #14, had no `bedrock:InvokeModel` grant at all before this change -- fail closed with
 * `AccessDeniedException` in a real account, which `npm run build` (a type-check only) cannot
 * catch.
 *
 * Usage: npx ts-node --prefer-ts-exts scripts/verify-bedrock-resources.ts
 */

import { App, Stack } from 'aws-cdk-lib';
import { getBedrockInvokeModelResources } from '../src/components/bedrock/invoke-model-resources';

let failures = 0;

function check(description: string, actual: unknown, expected: unknown): void {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    failures += 1;
    console.error(`FAIL: ${description}\n  expected: ${expectedJson}\n  actual:   ${actualJson}`);
  } else {
    console.log(`PASS: ${description}`);
  }
}

const app = new App();
const stack = new Stack(app, 'TestStack', {
  env: { account: '123456789012', region: 'us-east-1' },
});

// A plain foundation-model ID (e.g. the current-config-before-this-change value, or any model
// this codebase might roll back to) grants only a single-region foundation-model ARN.
check(
  'plain foundation-model ID grants a single foundation-model ARN',
  getBedrockInvokeModelResources(stack, 'us-east-1', 'anthropic.claude-3-haiku-20240307-v1:0'),
  ['arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0']
);

// The `us.` cross-region inference profile this spec configures grants the account-scoped
// profile ARN plus the foundation-model ARN in every region the profile can route to (confirmed
// via `aws bedrock list-inference-profiles` -- see the comment on CROSS_REGION_PROFILE_ROUTES).
check(
  '`us.` inference profile grants the profile ARN and every routed-to foundation-model ARN',
  getBedrockInvokeModelResources(stack, 'us-east-1', 'us.anthropic.claude-haiku-4-5-20251001-v1:0'),
  [
    'arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0',
    'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0',
    'arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0',
    'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0',
  ]
);

// A profile family this helper has no confirmed routing table for (e.g. `eu.`, `global.`) must
// fail loud rather than silently grant a single-region ARN that would under-grant the real
// profile -- an under-grant here means the Lambda fails closed with AccessDeniedException the
// first time AWS actually routes a request to an ungranted region, which is worse than a
// build-time error.
{
  const description = 'an unmapped profile family throws rather than under-granting';
  try {
    getBedrockInvokeModelResources(stack, 'eu-west-1', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0');
    failures += 1;
    console.error(`FAIL: ${description}\n  expected: a thrown error\n  actual:   no error thrown`);
  } catch (err) {
    console.log(`PASS: ${description}`);
  }
}

if (failures > 0) {
  console.error(`\n${failures} check(s) failed.`);
  process.exit(1);
}

console.log('\nAll checks passed.');
