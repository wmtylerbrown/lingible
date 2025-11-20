import { Duration, Stack } from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as eventTargets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';
import {
  AsyncResourceReferences,
  BaseStackProps,
  DataResourceReferences,
  SharedResourceReferences,
} from '../types';
import { createPythonLambda } from '../components/lambda/python-lambda';
import { buildLambdaEnvironment } from '../components/lambda/environment';

export interface AsyncConstructProps extends BaseStackProps {
  readonly shared: SharedResourceReferences;
  readonly data: DataResourceReferences;
}

export class AsyncConstruct extends Construct {
  public readonly asyncResources: AsyncResourceReferences;

  private readonly alertTopic: sns.Topic;
  private readonly slangSubmissionsTopic: sns.Topic;
  private readonly slangValidationRequestTopic: sns.Topic;
  private readonly deploymentEnvironment: string;

  public constructor(scope: Construct, id: string, props: AsyncConstructProps) {
    super(scope, id);

    this.deploymentEnvironment = props.envContext.environment;
    this.alertTopic = this.createTopic('AlertTopic', `lingible-alerts-${props.envContext.environment}`, `Lingible ${props.envContext.environment} Alerts`);
    this.slangSubmissionsTopic = this.createTopic(
      'SlangSubmissionsTopic',
      `lingible-slang-submissions-${props.envContext.environment}`,
      `Lingible ${props.envContext.environment} Slang Submissions`,
    );
    this.slangValidationRequestTopic = this.createTopic(
      'SlangValidationRequestTopic',
      `lingible-slang-validation-requests-${props.envContext.environment}`,
      `Lingible ${props.envContext.environment} Slang Validation Requests`,
    );

    this.asyncResources = {
      environment: props.envContext.environment,
      alertTopic: this.alertTopic,
      slangSubmissionsTopic: this.slangSubmissionsTopic,
      slangValidationRequestTopic: this.slangValidationRequestTopic,
    };

    const slangValidationProcessor = this.createSlangValidationProcessor(props);
    this.slangValidationRequestTopic.addSubscription(new snsSubscriptions.LambdaSubscription(slangValidationProcessor));

    const exportLexiconLambda = this.createExportLexiconLambda(props);
    this.slangSubmissionsTopic.addSubscription(
      new snsSubscriptions.LambdaSubscription(exportLexiconLambda, {
        filterPolicy: {
          notification_type: sns.SubscriptionFilter.stringFilter({
            allowlist: ['auto_approval', 'manual_approval'],
          }),
        },
      })
    );

    const userDataCleanupLambda = this.createUserDataCleanupLambda(props);
    const trendingJobLambda = this.createTrendingJobLambda(props);
    this.createTrendingSchedules(props, trendingJobLambda);
  }

  private createTopic(id: string, topicName: string, displayName: string): sns.Topic {
    return new sns.Topic(this, id, {
      topicName,
      displayName,
    });
  }

  private createSlangValidationProcessor(props: AsyncConstructProps) {
    const env = buildLambdaEnvironment(props.envContext, props.data, this.asyncResources)
      .includeSecurity()
      .includeUsersTable()
      .includeSubmissionsTable()
      .includeUsageLimits()
      .includeLexicon()
      .includeLlm()
      .includeSlangValidation()
      .includeSnsTopics()
      .build();
    const tavilyParameterArn = this.getSsmParameterArn(this.getTavilyApiKeyParameterPath());

    return createPythonLambda({
      scope: this,
      id: 'SlangValidationProcessor',
      functionName: `lingible-slang-validation-processor-${props.envContext.environment}`,
      handlerDirectory: 'slang_validation_async',
      environment: env,
      layers: [props.shared.layers.slangValidation, props.shared.layers.shared],
      memorySize: 512,
      timeout: Duration.seconds(60),
      grants: {
        readWriteTables: [props.data.submissionsTable, props.data.usersTable],
        publishTopics: [this.slangSubmissionsTopic],
        ssmParameters: [tavilyParameterArn],
      },
    });
  }

  private createExportLexiconLambda(props: AsyncConstructProps) {
    const env = {
      ...buildLambdaEnvironment(props.envContext, props.data, this.asyncResources)
        .includeSecurity()
        .includeLexiconTable()
        .includeLexicon()
        .build(),
      LEXICON_S3_BUCKET: props.data.lexiconBucket.bucketName,
    };

    return createPythonLambda({
      scope: this,
      id: 'ExportLexiconLambda',
      functionName: `lingible-export-lexicon-${props.envContext.environment}`,
      handlerDirectory: 'export_lexicon_async',
      environment: env,
      layers: [props.shared.layers.core, props.shared.layers.shared],
      timeout: Duration.minutes(5),
      grants: {
        readOnlyTables: [props.data.lexiconTable],
        writeBuckets: [props.data.lexiconBucket],
      },
    });
  }

  private createUserDataCleanupLambda(props: AsyncConstructProps) {
    const env = buildLambdaEnvironment(props.envContext, props.data, this.asyncResources)
      .includeSecurity()
      .includeUsersTable()
      .includeTranslationsTable()
      .includeUsageLimits()
      .includeLexicon()
      .includeLlm()
      .includeApple()
      .build();
    const appleParameterArn = this.getSsmParameterArn(this.getApplePrivateKeyParameterPath());

    return createPythonLambda({
      scope: this,
      id: 'UserDataCleanupLambda',
      functionName: `lingible-user-data-cleanup-${props.envContext.environment}`,
      handlerDirectory: 'user_data_cleanup_async',
      environment: env,
      layers: [props.shared.layers.receiptValidation, props.shared.layers.shared],
      timeout: Duration.seconds(60),
      memorySize: 384,
      grants: {
        readWriteTables: [props.data.usersTable, props.data.translationsTable],
        ssmParameters: [appleParameterArn],
      },
    });
  }

  private createTrendingJobLambda(props: AsyncConstructProps) {
    const env = buildLambdaEnvironment(props.envContext, props.data)
      .includeSecurity()
      .includeUsersTable()
      .includeTrendingTable()
      .includeUsageLimits()
      .includeLexicon()
      .includeLlm()
      .build();

    return createPythonLambda({
      scope: this,
      id: 'TrendingJobLambda',
      functionName: `lingible-trending-job-${props.envContext.environment}`,
      handlerDirectory: 'trending_job_async',
      environment: env,
      layers: [props.shared.layers.core, props.shared.layers.shared],
      timeout: Duration.seconds(60),
      grants: {
        readWriteTables: [props.data.trendingTable],
        readOnlyTables: [props.data.usersTable],
      },
    });
  }

  private createTrendingSchedules(props: AsyncConstructProps, trendingJobLambda: ReturnType<typeof createPythonLambda>) {
    const dailyRule = new events.Rule(this, 'TrendingJobSchedule', {
      ruleName: `lingible-trending-job-schedule-${props.envContext.environment}`,
      description: 'Daily schedule for trending term generation',
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '6',
        day: '*',
        month: '*',
        year: '*',
      }),
    });

    const payload = events.RuleTargetInput.fromObject({
      job_type: 'gen_z_slang_analysis',
      source: 'bedrock_ai',
      parameters: {
        model: props.envContext.backend.llm.model,
        max_terms: 20,
        categories: ['slang', 'meme', 'expression', 'hashtag', 'phrase'],
      },
    });

    dailyRule.addTarget(new eventTargets.LambdaFunction(trendingJobLambda, { event: payload }));
    trendingJobLambda.addPermission('EventBridgeTrendingJob', {
      principal: new iam.ServicePrincipal('events.amazonaws.com'),
      sourceArn: dailyRule.ruleArn,
    });

    const manualRule = new events.Rule(this, 'ManualTrendingJobTrigger', {
      ruleName: `lingible-manual-trending-job-${props.envContext.environment}`,
      description: 'Manual trigger for trending job testing',
      eventPattern: {
        source: ['lingible.manual'],
        detailType: ['Trending Job Request'],
      },
    });

    manualRule.addTarget(new eventTargets.LambdaFunction(trendingJobLambda, { event: payload }));
    trendingJobLambda.addPermission('EventBridgeManualTrendingJob', {
      principal: new iam.ServicePrincipal('events.amazonaws.com'),
      sourceArn: manualRule.ruleArn,
    });
  }

  private getApplePrivateKeyParameterPath(): string {
    return `/lingible/${this.deploymentEnvironment}/secrets/apple-iap-private-key`;
  }

  private getTavilyApiKeyParameterPath(): string {
    return `/lingible/${this.deploymentEnvironment}/secrets/tavily-api-key`;
  }

  private getSsmParameterArn(parameterPath: string): string {
    const normalized = parameterPath.startsWith('/') ? parameterPath.slice(1) : parameterPath;
    const stack = Stack.of(this);
    return stack.formatArn({
      service: 'ssm',
      resource: 'parameter',
      resourceName: normalized,
    });
  }
}
