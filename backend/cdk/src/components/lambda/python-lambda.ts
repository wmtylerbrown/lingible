import { Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';

export interface LambdaAccessGrants {
  readonly readWriteTables?: dynamodb.ITable[];
  readonly readOnlyTables?: dynamodb.ITable[];
  readonly readBuckets?: s3.IBucket[];
  readonly writeBuckets?: s3.IBucket[];
  readonly publishTopics?: sns.ITopic[];
  readonly additionalStatements?: iam.PolicyStatement[];
  readonly secretArns?: string[];
  readonly ssmParameters?: string[];
}

export interface PythonLambdaProps {
  readonly scope: Construct;
  readonly id: string;
  readonly functionName: string;
  readonly handlerDirectory: string;
  readonly environment: Record<string, string>;
  readonly layers: lambda.ILayerVersion[];
  readonly memorySize?: number;
  readonly timeout?: Duration;
  readonly logRetention?: logs.RetentionDays;
  readonly description?: string;
  readonly grants?: LambdaAccessGrants;
}

export function createPythonLambda(props: PythonLambdaProps): lambda.Function {
  const {
    scope,
    id,
    functionName,
    handlerDirectory,
    environment,
    layers,
    memorySize = 256,
    timeout = Duration.seconds(30),
    logRetention = logs.RetentionDays.ONE_WEEK,
    description,
    grants,
  } = props;

  const logGroup = new logs.LogGroup(scope, `${id}LogGroup`, {
    logGroupName: `/aws/lambda/${functionName}`,
    retention: logRetention,
    removalPolicy: RemovalPolicy.DESTROY,
  });

  const fn = new lambda.Function(scope, id, {
    functionName,
    runtime: lambda.Runtime.PYTHON_3_13,
    architecture: lambda.Architecture.ARM_64,
    handler: 'handler.handler',
    code: lambda.Code.fromAsset(`../lambda/src/handlers/${handlerDirectory}`, {
      bundling: {
        image: lambda.Runtime.PYTHON_3_13.bundlingImage,
        platform: 'linux/arm64',
        command: ['bash', '-c', 'cp handler.py /asset-output/'],
      },
      exclude: [
        '**/__pycache__/**',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',
        '**/.pytest_cache/**',
        '**/.coverage',
        '**/.mypy_cache/**',
      ],
    }),
    environment,
    layers,
    memorySize,
    timeout,
    logGroup,
    description,
  });

  applyGrants(fn, grants);

  return fn;
}

function applyGrants(fn: lambda.Function, grants?: LambdaAccessGrants): void {
  if (!grants) {
    return;
  }

  grants.readWriteTables?.forEach((table) => table.grantReadWriteData(fn));
  grants.readOnlyTables?.forEach((table) => table.grantReadData(fn));
  grants.readBuckets?.forEach((bucket) => bucket.grantRead(fn));
  grants.writeBuckets?.forEach((bucket) => bucket.grantWrite(fn));
  grants.publishTopics?.forEach((topic) => topic.grantPublish(fn));
  grants.additionalStatements?.forEach((statement) => fn.addToRolePolicy(statement));

  if (grants.secretArns?.length) {
    fn.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['secretsmanager:GetSecretValue'],
        resources: grants.secretArns,
      })
    );
  }

  if (grants.ssmParameters?.length) {
    fn.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter', 'ssm:GetParameters'],
        resources: grants.ssmParameters,
      })
    );
  }
}
