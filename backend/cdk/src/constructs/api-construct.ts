import { CfnOutput, Duration, RemovalPolicy, SecretValue, Stack } from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import {
  AsyncResourceReferences,
  BaseStackProps,
  DataResourceReferences,
  EnvironmentContext,
  SharedResourceReferences,
} from '../types';
import { createPythonLambda } from '../components/lambda/python-lambda';
import { buildLambdaEnvironment } from '../components/lambda/environment';

export interface ApiConstructProps extends BaseStackProps {
  readonly shared: SharedResourceReferences;
  readonly data: DataResourceReferences;
  readonly asyncResources: AsyncResourceReferences;
}

export class ApiConstruct extends Construct {
  private readonly ctx: EnvironmentContext;
  private readonly shared: SharedResourceReferences;
  private readonly data: DataResourceReferences;
  private readonly asyncResources: AsyncResourceReferences;

  private apiDomainName!: string;
  private authDomainName!: string;
  private certificate!: acm.Certificate;
  private authCertificate!: acm.Certificate;
  private userPool!: cognito.UserPool;
  private userPoolClient!: cognito.UserPoolClient;
  private userPoolDomain?: cognito.UserPoolDomain;
  private cfnUserPoolDomain?: cognito.CfnUserPoolDomain;
  private api!: apigateway.RestApi;

  private translateLambda!: lambda.Function;
  private userProfileLambda!: lambda.Function;
  private userUsageLambda!: lambda.Function;
  private userUpgradeLambda!: lambda.Function;
  private userAccountDeletionLambda!: lambda.Function;
  private translationHistoryLambda!: lambda.Function;
  private deleteTranslationLambda!: lambda.Function;
  private deleteAllTranslationsLambda!: lambda.Function;
  private healthLambda!: lambda.Function;
  private appleWebhookLambda!: lambda.Function;
  private postConfirmationLambda!: lambda.Function;
  private trendingLambda!: lambda.Function;
  private submitSlangLambda!: lambda.Function;
  private slangUpvoteLambda!: lambda.Function;
  private slangPendingLambda!: lambda.Function;
  private slangAdminApproveLambda!: lambda.Function;
  private slangAdminRejectLambda!: lambda.Function;
  private quizQuestionLambda!: lambda.Function;
  private quizAnswerLambda!: lambda.Function;
  private quizHistoryLambda!: lambda.Function;
  private quizProgressLambda!: lambda.Function;
  private quizEndLambda!: lambda.Function;
  private dashboard?: cloudwatch.Dashboard;
  private readonly stack: Stack;

  public constructor(scope: Construct, id: string, props: ApiConstructProps) {
    super(scope, id);

    this.ctx = props.envContext;
    this.shared = props.shared;
    this.data = props.data;
    this.asyncResources = props.asyncResources;

    // Ensure we're within a Stack for Stack.of() calls
    this.stack = Stack.of(this);

    this.createCertificates();
    this.createUserPool();
    this.createApiLambdas();
    this.setupCognitoTriggers();
    this.createApiGateway();
    this.createMonitoring();
    this.createOutputs();
  }

  private createCertificates(): void {
    const zoneName = this.ctx.environment === 'prod' ? 'lingible.com' : `${this.ctx.environment}.lingible.com`;

    this.apiDomainName = this.ctx.environment === 'prod' ? 'api.lingible.com' : `api.${zoneName}`;
    this.certificate = new acm.Certificate(this, 'ApiCertificate', {
      domainName: this.apiDomainName,
      validation: acm.CertificateValidation.fromDns(),
    });

    this.authDomainName = this.ctx.environment === 'prod' ? 'auth.lingible.com' : `auth.${zoneName}`;
    this.authCertificate = new acm.Certificate(this, 'AuthCertificate', {
      domainName: this.authDomainName,
      validation: acm.CertificateValidation.fromDns(),
    });
  }

  private createUserPool(): void {
    this.userPool = new cognito.UserPool(this, 'LingibleUserPool', {
      userPoolName: `lingible-user-pool-${this.ctx.environment}`,
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      autoVerify: { email: true },
      standardAttributes: {
        email: { required: true, mutable: true },
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const appleProvider = new cognito.UserPoolIdentityProviderApple(this, 'AppleProvider', {
      userPool: this.userPool,
      clientId: this.ctx.infrastructure.apple.client_id || 'TO_BE_SET',
      teamId: this.ctx.infrastructure.apple.team_id || 'TO_BE_SET',
      keyId: this.ctx.infrastructure.apple.key_id || 'TO_BE_SET',
      privateKeyValue: SecretValue.secretsManager(`lingible-apple-private-key-${this.ctx.environment}`, {
        jsonField: 'privateKey',
      }),
      scopes: ['openid', 'email', 'name'],
      attributeMapping: {
        email: cognito.ProviderAttribute.AMAZON_EMAIL,
      },
    });

    this.userPoolClient = new cognito.UserPoolClient(this, 'LingibleUserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: `lingible-client-${this.ctx.environment}`,
      generateSecret: false,
      authFlows: {
        adminUserPassword: true,
        userPassword: true,
        userSrp: true,
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
          implicitCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          this.ctx.environment === 'dev'
            ? 'com.lingible.lingible.dev://auth/callback'
            : 'com.lingible.lingible://auth/callback',
        ],
        logoutUrls: [
          this.ctx.environment === 'dev'
            ? 'com.lingible.lingible.dev://auth/logout'
            : 'com.lingible.lingible://auth/logout',
        ],
      },
      supportedIdentityProviders: [cognito.UserPoolClientIdentityProvider.APPLE],
      preventUserExistenceErrors: true,
    });
    this.userPoolClient.node.addDependency(appleProvider);

    // Create UserPoolDomain with custom domain (certificate must be validated)
    // Using Cfn construct directly for better control and error handling
    this.cfnUserPoolDomain = new cognito.CfnUserPoolDomain(this, 'LingibleUserPoolDomain', {
      domain: this.authDomainName,
      userPoolId: this.userPool.userPoolId,
      customDomainConfig: {
        certificateArn: this.authCertificate.certificateArn,
      },
    });
    // Explicit dependency to ensure certificate validation completes first
    this.cfnUserPoolDomain.addDependency(this.authCertificate.node.defaultChild as acm.CfnCertificate);
    // Store reference for outputs (using high-level construct for compatibility)
    this.userPoolDomain = {
      domainName: this.authDomainName,
      cloudFrontEndpoint: this.cfnUserPoolDomain.attrCloudFrontDistribution,
    } as cognito.UserPoolDomain;
  }

  private createApiLambdas(): void {
    const defaultLayers = [this.shared.layers.core, this.shared.layers.shared];
    const receiptLayers = [this.shared.layers.receiptValidation, this.shared.layers.shared];

    const baseEnv = () => buildLambdaEnvironment(this.ctx, this.data, this.asyncResources).includeSecurity();
    const translationEnv = () =>
      baseEnv()
        .includeUsersTable()
        .includeTranslationsTable()
        .includeUsageLimits()
        .includeLexicon()
        .includeLlm()
        .build();
    const userEnv = () => baseEnv().includeUsersTable().includeUsageLimits().build();
    const appleEnv = () => baseEnv().includeUsersTable().includeUsageLimits().includeApple().build();
    const appleTranslationEnv = () =>
      baseEnv()
        .includeUsersTable()
        .includeTranslationsTable()
        .includeUsageLimits()
        .includeLexicon()
        .includeLlm()
        .includeApple()
        .build();
    const quizEnv = () =>
      baseEnv().includeUsersTable().includeLexiconTable().includeUsageLimits().includeQuiz().build();
    const trendingEnv = () =>
      baseEnv()
        .includeUsersTable()
        .includeTrendingTable()
        .includeUsageLimits()
        .includeLexicon()
        .includeLlm()
        .build();
    const slangEnv = () =>
      baseEnv()
        .includeUsersTable()
        .includeSubmissionsTable()
        .includeUsageLimits()
        .includeLexicon()
        .includeLlm()
        .includeSlangValidation()
        .includeSnsTopics()
        .build();

    const applePrivateKeyArn = this.getSsmParameterArn(this.getApplePrivateKeyParameterPath());
    const tavilyApiKeyArn = this.getSsmParameterArn(this.getTavilyApiKeyParameterPath());

    this.translateLambda = createPythonLambda({
      scope: this,
      id: 'TranslateLambda',
      functionName: `lingible-translate-${this.ctx.environment}`,
      handlerDirectory: 'translate_api',
      environment: translationEnv(),
      layers: defaultLayers,
      memorySize: 512,
      timeout: Duration.seconds(30),
      grants: {
        readWriteTables: [this.data.usersTable, this.data.translationsTable],
        readOnlyTables: [this.data.lexiconTable],
      },
    });
    this.translateLambda.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:${this.ctx.infrastructure.bedrock.region}::foundation-model/${this.ctx.backend.llm.model}`,
        ],
      })
    );

    this.userProfileLambda = createPythonLambda({
      scope: this,
      id: 'UserProfileLambda',
      functionName: `lingible-user-profile-${this.ctx.environment}`,
      handlerDirectory: 'user_profile_api',
      environment: userEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable],
      },
    });

    this.userUsageLambda = createPythonLambda({
      scope: this,
      id: 'UserUsageLambda',
      functionName: `lingible-user-usage-${this.ctx.environment}`,
      handlerDirectory: 'user_usage_api',
      environment: userEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable],
      },
    });

    this.userUpgradeLambda = createPythonLambda({
      scope: this,
      id: 'UserUpgradeLambda',
      functionName: `lingible-user-upgrade-${this.ctx.environment}`,
      handlerDirectory: 'user_upgrade_api',
      environment: appleEnv(),
      layers: receiptLayers,
      memorySize: 384,
      grants: {
        readWriteTables: [this.data.usersTable],
        ssmParameters: [applePrivateKeyArn],
      },
    });

    this.userAccountDeletionLambda = createPythonLambda({
      scope: this,
      id: 'UserAccountDeletionLambda',
      functionName: `lingible-user-account-deletion-${this.ctx.environment}`,
      handlerDirectory: 'user_account_deletion_api',
      environment: {
        ...appleTranslationEnv(),
        COGNITO_USER_POOL_ID: this.userPool.userPoolId,
        COGNITO_USER_POOL_CLIENT_ID: this.userPoolClient.userPoolClientId,
        COGNITO_USER_POOL_REGION: this.stack.region,
        API_GATEWAY_ARN: `arn:aws:execute-api:${this.node.tryGetContext('region') || 'us-east-1'}:${this.node.tryGetContext('account') || '*'}:*/*`,
      },
      layers: receiptLayers,
      memorySize: 384,
      grants: {
        readWriteTables: [this.data.usersTable, this.data.translationsTable],
        ssmParameters: [applePrivateKeyArn],
        additionalStatements: [
          new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['cognito-idp:AdminDeleteUser'],
            resources: [this.userPool.userPoolArn],
          }),
        ],
      },
    });

    this.translationHistoryLambda = createPythonLambda({
      scope: this,
      id: 'TranslationHistoryLambda',
      functionName: `lingible-translation-history-${this.ctx.environment}`,
      handlerDirectory: 'get_translation_history_api',
      environment: translationEnv(),
      layers: defaultLayers,
      grants: {
        readOnlyTables: [this.data.translationsTable, this.data.usersTable],
      },
    });

    this.deleteTranslationLambda = createPythonLambda({
      scope: this,
      id: 'DeleteTranslationLambda',
      functionName: `lingible-delete-translation-${this.ctx.environment}`,
      handlerDirectory: 'delete_translation_api',
      environment: translationEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.translationsTable],
        readOnlyTables: [this.data.usersTable],
      },
    });

    this.deleteAllTranslationsLambda = createPythonLambda({
      scope: this,
      id: 'DeleteAllTranslationsLambda',
      functionName: `lingible-delete-all-translations-${this.ctx.environment}`,
      handlerDirectory: 'delete_translations_api',
      environment: translationEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.translationsTable],
        readOnlyTables: [this.data.usersTable],
      },
    });

    this.healthLambda = createPythonLambda({
      scope: this,
      id: 'HealthLambda',
      functionName: `lingible-health-${this.ctx.environment}`,
      handlerDirectory: 'health_api',
      environment: baseEnv().build(),
      layers: defaultLayers,
      memorySize: 128,
      timeout: Duration.seconds(10),
    });

    this.trendingLambda = createPythonLambda({
      scope: this,
      id: 'TrendingLambda',
      functionName: `lingible-trending-${this.ctx.environment}`,
      handlerDirectory: 'trending_api',
      environment: trendingEnv(),
      layers: defaultLayers,
      grants: {
        readOnlyTables: [this.data.trendingTable, this.data.usersTable],
      },
    });

    this.submitSlangLambda = createPythonLambda({
      scope: this,
      id: 'SubmitSlangLambda',
      functionName: `lingible-submit-slang-${this.ctx.environment}`,
      handlerDirectory: 'submit_slang_api',
      environment: slangEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.submissionsTable, this.data.usersTable],
        publishTopics: [this.asyncResources.slangSubmissionsTopic, this.asyncResources.slangValidationRequestTopic],
        ssmParameters: [tavilyApiKeyArn],
      },
    });

    this.slangUpvoteLambda = createPythonLambda({
      scope: this,
      id: 'SlangUpvoteLambda',
      functionName: `lingible-slang-upvote-${this.ctx.environment}`,
      handlerDirectory: 'slang_upvote_api',
      environment: slangEnv(),
      layers: defaultLayers,
      timeout: Duration.seconds(15),
      grants: {
        readWriteTables: [this.data.submissionsTable, this.data.usersTable],
        publishTopics: [this.asyncResources.slangSubmissionsTopic, this.asyncResources.slangValidationRequestTopic],
        ssmParameters: [tavilyApiKeyArn],
      },
    });

    this.slangPendingLambda = createPythonLambda({
      scope: this,
      id: 'SlangPendingLambda',
      functionName: `lingible-slang-pending-${this.ctx.environment}`,
      handlerDirectory: 'slang_pending_api',
      environment: slangEnv(),
      layers: defaultLayers,
      timeout: Duration.seconds(15),
      grants: {
        readOnlyTables: [this.data.submissionsTable],
        ssmParameters: [tavilyApiKeyArn],
      },
    });

    this.slangAdminApproveLambda = createPythonLambda({
      scope: this,
      id: 'SlangAdminApproveLambda',
      functionName: `lingible-slang-admin-approve-${this.ctx.environment}`,
      handlerDirectory: 'slang_admin_approve_api',
      environment: slangEnv(),
      layers: defaultLayers,
      timeout: Duration.seconds(15),
      grants: {
        readWriteTables: [this.data.submissionsTable],
        ssmParameters: [tavilyApiKeyArn],
      },
    });

    this.slangAdminRejectLambda = createPythonLambda({
      scope: this,
      id: 'SlangAdminRejectLambda',
      functionName: `lingible-slang-admin-reject-${this.ctx.environment}`,
      handlerDirectory: 'slang_admin_reject_api',
      environment: slangEnv(),
      layers: defaultLayers,
      timeout: Duration.seconds(15),
      grants: {
        readWriteTables: [this.data.submissionsTable],
        ssmParameters: [tavilyApiKeyArn],
      },
    });

    this.quizQuestionLambda = createPythonLambda({
      scope: this,
      id: 'QuizQuestionLambda',
      functionName: `lingible-quiz-question-${this.ctx.environment}`,
      handlerDirectory: 'quiz_question_api',
      environment: quizEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable],
        readOnlyTables: [this.data.lexiconTable],
      },
    });

    this.quizAnswerLambda = createPythonLambda({
      scope: this,
      id: 'QuizAnswerLambda',
      functionName: `lingible-quiz-answer-${this.ctx.environment}`,
      handlerDirectory: 'quiz_answer_api',
      environment: quizEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable, this.data.lexiconTable],
      },
    });

    this.quizHistoryLambda = createPythonLambda({
      scope: this,
      id: 'QuizHistoryLambda',
      functionName: `lingible-quiz-history-${this.ctx.environment}`,
      handlerDirectory: 'quiz_history_api',
      environment: quizEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable],
        readOnlyTables: [this.data.lexiconTable],
      },
    });

    this.quizProgressLambda = createPythonLambda({
      scope: this,
      id: 'QuizProgressLambda',
      functionName: `lingible-quiz-progress-${this.ctx.environment}`,
      handlerDirectory: 'quiz_progress_api',
      environment: quizEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable],
        readOnlyTables: [this.data.lexiconTable],
      },
    });

    this.quizEndLambda = createPythonLambda({
      scope: this,
      id: 'QuizEndLambda',
      functionName: `lingible-quiz-end-${this.ctx.environment}`,
      handlerDirectory: 'quiz_end_api',
      environment: quizEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable],
        readOnlyTables: [this.data.lexiconTable],
      },
    });

    this.appleWebhookLambda = createPythonLambda({
      scope: this,
      id: 'AppleWebhookLambda',
      functionName: `lingible-apple-webhook-${this.ctx.environment}`,
      handlerDirectory: 'apple_webhook_api',
      environment: appleEnv(),
      layers: receiptLayers,
      memorySize: 384,
      grants: {
        readWriteTables: [this.data.usersTable],
        ssmParameters: [applePrivateKeyArn],
      },
    });

    this.postConfirmationLambda = createPythonLambda({
      scope: this,
      id: 'PostConfirmationLambda',
      functionName: `lingible-post-confirmation-${this.ctx.environment}`,
      handlerDirectory: 'cognito_post_confirmation_trigger',
      environment: userEnv(),
      layers: defaultLayers,
      grants: {
        readWriteTables: [this.data.usersTable],
      },
    });
  }

  private setupCognitoTriggers(): void {
    this.userPool.addTrigger(cognito.UserPoolOperation.POST_CONFIRMATION, this.postConfirmationLambda);
    this.postConfirmationLambda.addPermission('CognitoPostConfirmation', {
      principal: new iam.ServicePrincipal('cognito-idp.amazonaws.com'),
      sourceArn: this.userPool.userPoolArn,
    });
  }

  private createApiGateway(): void {
    this.api = new apigateway.RestApi(this, 'LingibleApi', {
      restApiName: `lingible-api-${this.ctx.environment}`,
      description: `Lingible API for ${this.ctx.environment} environment`,
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: apigateway.Cors.DEFAULT_HEADERS,
      },
      domainName: {
        domainName: this.apiDomainName,
        certificate: this.certificate,
      },
      deployOptions: {
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: false,
        metricsEnabled: true,
        accessLogDestination: new apigateway.LogGroupLogDestination(
          new logs.LogGroup(this, 'ApiAccessLogs', {
            logGroupName: `/aws/apigateway/${this.ctx.projectName}/${this.ctx.environment}`,
            retention: logs.RetentionDays.ONE_WEEK,
          })
        ),
        accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields({
          caller: true,
          httpMethod: true,
          ip: true,
          protocol: true,
          requestTime: true,
          resourcePath: true,
          responseLength: true,
          status: true,
          user: true,
        }),
      },
    });

    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'NativeCognitoAuthorizer', {
      cognitoUserPools: [this.userPool],
      authorizerName: 'NativeCognitoAuthorizer',
      identitySource: 'method.request.header.Authorization',
    });

    const errorModel = this.api.addModel('ErrorModel', {
      contentType: 'application/json',
      modelName: 'LingibleError',
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          message: { type: apigateway.JsonSchemaType.STRING },
          error: { type: apigateway.JsonSchemaType.STRING },
        },
      },
    });

    const successModel = this.api.addModel('SuccessModel', {
      contentType: 'application/json',
      modelName: 'LingibleSuccess',
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          message: { type: apigateway.JsonSchemaType.STRING },
          data: { type: apigateway.JsonSchemaType.OBJECT },
        },
      },
    });

    this.createApiResources(cognitoAuthorizer, errorModel, successModel);
    this.grantApiGatewayPermissions();
  }

  private createApiResources(
    cognitoAuthorizer: apigateway.CognitoUserPoolsAuthorizer,
    errorModel: apigateway.Model,
    successModel: apigateway.Model
  ): void {
    const authResponses = [
      {
        statusCode: '200',
        responseModels: { 'application/json': successModel },
      },
      {
        statusCode: '401',
        responseModels: { 'application/json': errorModel },
      },
    ];

    const health = this.api.root.addResource('health');
    health.addMethod('GET', new apigateway.LambdaIntegration(this.healthLambda), {
      methodResponses: [
        {
          statusCode: '200',
          responseModels: { 'application/json': successModel },
        },
      ],
    });

    const translate = this.api.root.addResource('translate');
    translate.addMethod('POST', new apigateway.LambdaIntegration(this.translateLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const user = this.api.root.addResource('user');
    const profile = user.addResource('profile');
    profile.addMethod('GET', new apigateway.LambdaIntegration(this.userProfileLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const usage = user.addResource('usage');
    usage.addMethod('GET', new apigateway.LambdaIntegration(this.userUsageLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const upgrade = user.addResource('upgrade');
    upgrade.addMethod('POST', new apigateway.LambdaIntegration(this.userUpgradeLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const account = user.addResource('account');
    account.addMethod('DELETE', new apigateway.LambdaIntegration(this.userAccountDeletionLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: [
        { statusCode: '200', responseModels: { 'application/json': successModel } },
        { statusCode: '400', responseModels: { 'application/json': errorModel } },
        { statusCode: '401', responseModels: { 'application/json': errorModel } },
        { statusCode: '500', responseModels: { 'application/json': errorModel } },
      ],
    });

    const translations = this.api.root.addResource('translations');
    translations.addMethod('GET', new apigateway.LambdaIntegration(this.translationHistoryLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const translationId = translations.addResource('{translationId}');
    translationId.addMethod('DELETE', new apigateway.LambdaIntegration(this.deleteTranslationLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const deleteAll = translations.addResource('all');
    deleteAll.addMethod('DELETE', new apigateway.LambdaIntegration(this.deleteAllTranslationsLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const trending = this.api.root.addResource('trending');
    trending.addMethod('GET', new apigateway.LambdaIntegration(this.trendingLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: authResponses,
    });

    const slang = this.api.root.addResource('slang');
    slang
      .addResource('submit')
      .addMethod('POST', new apigateway.LambdaIntegration(this.submitSlangLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    slang
      .addResource('pending')
      .addMethod('GET', new apigateway.LambdaIntegration(this.slangPendingLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    slang
      .addResource('upvote')
      .addMethod('POST', new apigateway.LambdaIntegration(this.slangUpvoteLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    slang
      .addResource('approve')
      .addMethod('POST', new apigateway.LambdaIntegration(this.slangAdminApproveLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    slang
      .addResource('reject')
      .addMethod('POST', new apigateway.LambdaIntegration(this.slangAdminRejectLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });

    const quiz = this.api.root.addResource('quiz');
    // GET /quiz/question - get next question (stateless API)
    quiz
      .addResource('question')
      .addMethod('GET', new apigateway.LambdaIntegration(this.quizQuestionLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    // POST /quiz/answer - submit answer for one question (stateless API)
    quiz
      .addResource('answer')
      .addMethod('POST', new apigateway.LambdaIntegration(this.quizAnswerLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    quiz
      .addResource('history')
      .addMethod('GET', new apigateway.LambdaIntegration(this.quizHistoryLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    quiz
      .addResource('progress')
      .addMethod('GET', new apigateway.LambdaIntegration(this.quizProgressLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });
    quiz
      .addResource('end')
      .addMethod('POST', new apigateway.LambdaIntegration(this.quizEndLambda), {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: authResponses,
      });

    const webhooks = this.api.root.addResource('webhooks');
    webhooks.addResource('apple').addMethod('POST', new apigateway.LambdaIntegration(this.appleWebhookLambda), {
      methodResponses: [{ statusCode: '200', responseModels: { 'application/json': successModel } }],
    });
  }

  private grantApiGatewayPermissions(): void {
    const sourceArn = `arn:aws:execute-api:${this.stack.region}:${this.stack.account}:${this.api.restApiId}/*`;
    const allowInvoke = (fn: lambda.Function, id: string) => {
      fn.addPermission(id, {
        principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
        sourceArn,
      });
    };

    [
      this.healthLambda,
      this.translateLambda,
      this.userProfileLambda,
      this.userUsageLambda,
      this.userUpgradeLambda,
      this.userAccountDeletionLambda,
      this.translationHistoryLambda,
      this.deleteTranslationLambda,
      this.deleteAllTranslationsLambda,
      this.trendingLambda,
      this.submitSlangLambda,
      this.slangUpvoteLambda,
      this.slangPendingLambda,
      this.slangAdminApproveLambda,
      this.slangAdminRejectLambda,
      this.quizQuestionLambda,
      this.quizAnswerLambda,
      this.quizHistoryLambda,
      this.quizProgressLambda,
      this.quizEndLambda,
      this.appleWebhookLambda,
    ].forEach((fn, index) => allowInvoke(fn, `ApiGatewayInvoke${index}`));
  }

  private getApplePrivateKeyParameterPath(): string {
    return `/lingible/${this.ctx.environment}/secrets/apple-iap-private-key`;
  }

  private getTavilyApiKeyParameterPath(): string {
    return `/lingible/${this.ctx.environment}/secrets/tavily-api-key`;
  }

  private getSsmParameterArn(parameterPath: string): string {
    const normalized = parameterPath.startsWith('/') ? parameterPath.slice(1) : parameterPath;
    return this.stack.formatArn({
      service: 'ssm',
      resource: 'parameter',
      resourceName: normalized,
    });
  }

  private createMonitoring(): void {
    this.dashboard = new cloudwatch.Dashboard(this, 'LingibleDashboard', {
      dashboardName: `Lingible-${this.ctx.environment}`,
    });

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Invocations',
        left: [
          this.translateLambda.metricInvocations(),
          this.userProfileLambda.metricInvocations(),
          this.translationHistoryLambda.metricInvocations(),
          this.trendingLambda.metricInvocations(),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Errors',
        left: [
          this.translateLambda.metricErrors(),
          this.userProfileLambda.metricErrors(),
          this.translationHistoryLambda.metricErrors(),
          this.trendingLambda.metricErrors(),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration',
        left: [
          this.translateLambda.metricDuration(),
          this.userProfileLambda.metricDuration(),
          this.translationHistoryLambda.metricDuration(),
          this.trendingLambda.metricDuration(),
        ],
      })
    );

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Gateway Requests',
        left: [this.api.metricCount()],
      })
    );

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'DynamoDB Read Capacity',
        left: [
          this.data.usersTable.metricConsumedReadCapacityUnits(),
          this.data.translationsTable.metricConsumedReadCapacityUnits(),
          this.data.submissionsTable.metricConsumedReadCapacityUnits(),
          this.data.lexiconTable.metricConsumedReadCapacityUnits(),
          this.data.trendingTable.metricConsumedReadCapacityUnits(),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'DynamoDB Write Capacity',
        left: [
          this.data.usersTable.metricConsumedWriteCapacityUnits(),
          this.data.translationsTable.metricConsumedWriteCapacityUnits(),
          this.data.submissionsTable.metricConsumedWriteCapacityUnits(),
          this.data.lexiconTable.metricConsumedWriteCapacityUnits(),
          this.data.trendingTable.metricConsumedWriteCapacityUnits(),
        ],
      })
    );

    new cloudwatch.Alarm(this, 'HighLambdaErrors', {
      metric: this.translateLambda.metricErrors(),
      threshold: 10,
      evaluationPeriods: 2,
      alarmDescription: 'High Lambda error rate',
    }).addAlarmAction(new actions.SnsAction(this.asyncResources.alertTopic));
  }

  private createOutputs(): void {
    new CfnOutput(this, 'UsersTableName', {
      value: this.data.usersTable.tableName,
    });
    new CfnOutput(this, 'TranslationsTableName', {
      value: this.data.translationsTable.tableName,
    });
    new CfnOutput(this, 'SubmissionsTableName', {
      value: this.data.submissionsTable.tableName,
    });
    new CfnOutput(this, 'LexiconTableName', {
      value: this.data.lexiconTable.tableName,
    });
    new CfnOutput(this, 'TrendingTableName', {
      value: this.data.trendingTable.tableName,
    });
    new CfnOutput(this, 'ApiEndpoint', {
      value: this.api.url,
    });
    new CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
    });
    new CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
    });

    const apiAliasTarget =
      this.api.domainName?.domainNameAliasDomainName ?? 'See AWS console for API Gateway domain target';
    new CfnOutput(this, 'ApiManualDNSInstructions', {
      value: `Create a CNAME for ${this.apiDomainName} pointing to ${apiAliasTarget}. CloudFormation will pause until you add the ACM validation CNAMEs in Squarespace.`,
    });

    // Custom Cognito domain
    const authTarget =
      this.cfnUserPoolDomain?.attrCloudFrontDistribution ?? 'See AWS console for Cognito custom domain target';
    new CfnOutput(this, 'AuthManualDNSInstructions', {
      value: `Create a CNAME for ${this.authDomainName} pointing to ${authTarget}. Certificate is validated.`,
      description: 'DNS configuration for Cognito custom domain',
    });
  }
}
