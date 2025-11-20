import { Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { BaseStackProps } from '../types';
import { SharedConstruct } from '../constructs/shared-construct';
import { DataConstruct } from '../constructs/data-construct';
import { AsyncConstruct } from '../constructs/async-construct';
import { ApiConstruct } from '../constructs/api-construct';

/**
 * Combined Backend Stack
 *
 * This stack combines Shared, Data, Async, and Api resources into a single stack
 * to avoid CloudFormation cross-stack reference issues. The logical separation
 * is maintained through internal constructs, but everything deploys together.
 */
export class BackendStack extends Stack {
  public constructor(scope: Construct, id: string, props: BaseStackProps) {
    super(scope, id, props);

    // Step 1: Create shared resources (Lambda layers)
    const sharedConstruct = new SharedConstruct(this, 'Shared', props);

    // Step 2: Create data resources (DynamoDB tables, S3 buckets)
    const dataConstruct = new DataConstruct(this, 'Data', {
      ...props,
      shared: sharedConstruct.shared,
    });

    // Step 3: Create async resources (SNS topics)
    const asyncConstruct = new AsyncConstruct(this, 'Async', {
      ...props,
      shared: sharedConstruct.shared,
      data: dataConstruct.data,
    });

    // Step 4: Create API resources (Cognito, API Gateway, Lambda functions)
    const apiConstruct = new ApiConstruct(this, 'Api', {
      ...props,
      shared: sharedConstruct.shared,
      data: dataConstruct.data,
      asyncResources: asyncConstruct.asyncResources,
    });
  }
}
