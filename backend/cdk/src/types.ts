import { StackProps } from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import {
  BackendConfig,
  InfrastructureConfig,
} from './config/types';

export type DeploymentEnvironment = 'dev' | 'prod' | 'staging';

export interface EnvironmentContext {
  readonly environment: DeploymentEnvironment;
  readonly projectName: string;
  readonly backend: BackendConfig;
  readonly infrastructure: InfrastructureConfig;
}

export interface BaseStackProps extends StackProps {
  readonly envContext: EnvironmentContext;
}

export interface SharedResourceReferences {
  readonly environment: DeploymentEnvironment;
  readonly layers: {
    readonly shared: lambda.LayerVersion;
    readonly core: lambda.LayerVersion;
    readonly receiptValidation: lambda.LayerVersion;
    readonly slangValidation: lambda.LayerVersion;
  };
}

export interface DataResourceReferences {
  readonly environment: DeploymentEnvironment;
  readonly usersTable: dynamodb.Table;
  readonly translationsTable: dynamodb.Table;
  readonly submissionsTable: dynamodb.Table;
  readonly lexiconTable: dynamodb.Table;
  readonly trendingTable: dynamodb.Table;
  readonly lexiconBucket: s3.Bucket;
}

export interface AsyncResourceReferences {
  readonly environment: DeploymentEnvironment;
  readonly alertTopic: sns.Topic;
  readonly slangSubmissionsTopic: sns.Topic;
  readonly slangValidationRequestTopic: sns.Topic;
}
