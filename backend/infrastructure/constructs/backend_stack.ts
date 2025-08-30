import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';

import { Duration, RemovalPolicy, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as fs from 'fs';
import * as path from 'path';

export class BackendStack extends cdk.Stack {
  // Database resources
  public usersTable!: dynamodb.Table;
  public translationsTable!: dynamodb.Table;

  // Cognito resources
  public userPool!: cognito.UserPool;
  public userPoolClient!: cognito.UserPoolClient;

  // Shared Lambda layer
  public sharedLayer!: lambda.LayerVersion;

  // Lambda functions
  public authorizerLambda!: lambda.Function;
  public translateLambda!: lambda.Function;
  public userProfileLambda!: lambda.Function;
  public userUsageLambda!: lambda.Function;
  public userUpgradeLambda!: lambda.Function;
  public translationHistoryLambda!: lambda.Function;
  public deleteTranslationLambda!: lambda.Function;
  public deleteAllTranslationsLambda!: lambda.Function;
  public healthLambda!: lambda.Function;
  public appleWebhookLambda!: lambda.Function;
  public postConfirmationLambda!: lambda.Function;
  public preAuthenticationLambda!: lambda.Function;
  public preUserDeletionLambda!: lambda.Function;
  public userDataCleanupLambda!: lambda.Function;

  // API Gateway resources
  public api!: apigateway.RestApi;
  public certificate!: acm.Certificate;

  // Monitoring resources
  public dashboard!: cloudwatch.Dashboard;
  public alertTopic!: sns.Topic;

  constructor(
    scope: Construct,
    id: string,
    props: cdk.StackProps & {
      environment: string;
      hostedZone: route53.IHostedZone;
      appleClientId?: string;
      appleTeamId?: string;
      appleKeyId?: string;
    }
  ) {
    super(scope, id, props);

    const { environment, hostedZone, appleClientId, appleTeamId, appleKeyId } = props;

    // Common Lambda configuration
    const lambdaConfig = {
      runtime: lambda.Runtime.PYTHON_3_13,
      timeout: Duration.seconds(30),
      memorySize: 512,
      logRetention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY, // For development
    };

    // Create shared Lambda layer for common code
    this.sharedLayer = this.createSharedLayer(environment);

    // Create DynamoDB tables
    this.createDatabaseTables(environment);

    // Common environment variables
    const commonEnv = {
      POWERTOOLS_SERVICE_NAME: 'lingible-api',
      LOG_LEVEL: 'INFO',
      USERS_TABLE: this.usersTable.tableName,
      TRANSLATIONS_TABLE: this.translationsTable.tableName,
    };

    // Common IAM policy statements for Lambda functions
    const lambdaPolicyStatements = [
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'dynamodb:GetItem',
          'dynamodb:PutItem',
          'dynamodb:UpdateItem',
          'dynamodb:DeleteItem',
          'dynamodb:Query',
          'dynamodb:Scan',
        ],
        resources: [
          this.usersTable.tableArn,
          this.translationsTable.tableArn,
          `${this.usersTable.tableArn}/index/*`,
          `${this.translationsTable.tableArn}/index/*`,
        ],
      }),
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        resources: ['*'],
      }),
    ];

    // Create Cognito User Pool
    this.createCognitoUserPool(environment, appleClientId, appleTeamId, appleKeyId);

    // Create Lambda functions
    this.createLambdaFunctions(environment, commonEnv, lambdaConfig, lambdaPolicyStatements);

    // Configure Cognito triggers
    this.setupCognitoTriggers();

    // Create API Gateway
    this.createApiGateway(environment, hostedZone);

    // Create monitoring
    this.createMonitoring(environment);

    // Add tags to all resources
    cdk.Tags.of(this).add('Application', 'Lingible');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Component', 'Backend');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');

    // Outputs
    this.createOutputs(environment);
  }

  private createDatabaseTables(environment: string): void {
    // Users table
    this.usersTable = new dynamodb.Table(this, 'UsersTable', {
      tableName: `lingible-users-${environment}`,
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      pointInTimeRecovery: true,
    });

    // Add GSI for email lookups
    this.usersTable.addGlobalSecondaryIndex({
      indexName: 'email-index',
      partitionKey: {
        name: 'email',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Translations table
    this.translationsTable = new dynamodb.Table(this, 'TranslationsTable', {
      tableName: `lingible-translations-${environment}`,
      partitionKey: {
        name: 'translation_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      pointInTimeRecovery: true,
    });

    // Add GSI for user translations
    this.translationsTable.addGlobalSecondaryIndex({
      indexName: 'user-translations-index',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });
  }

  private createCognitoUserPool(
    environment: string,
    appleClientId?: string,
    appleTeamId?: string,
    appleKeyId?: string
  ): void {
    this.userPool = new cognito.UserPool(this, 'LingibleUserPool', {
      userPoolName: `lingible-user-pool-${environment}`,
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: RemovalPolicy.DESTROY, // For development
    });

    // Add Apple Identity Provider with secret lookup
    new cognito.UserPoolIdentityProviderApple(this, 'AppleProvider', {
      userPool: this.userPool,
      clientId: appleClientId || 'TO_BE_SET',
      teamId: appleTeamId || 'TO_BE_SET',
      keyId: appleKeyId || 'TO_BE_SET',
      privateKeyValue: cdk.SecretValue.secretsManager(`lingible-apple-private-key-${environment}`, {
        jsonField: 'privateKey',
      }),
      scopes: ['email', 'name'],
      attributeMapping: {
        email: cognito.ProviderAttribute.AMAZON_EMAIL,
      },
    });

    // Create User Pool Client
    this.userPoolClient = new cognito.UserPoolClient(this, 'LingibleUserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: `lingible-client-${environment}`,
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
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          `https://${environment}.lingible.com/auth/callback`,
          'http://localhost:3000/auth/callback', // For local development
        ],
        logoutUrls: [
          `https://${environment}.lingible.com/auth/logout`,
          'http://localhost:3000/auth/logout', // For local development
        ],
      },
      preventUserExistenceErrors: true,
    });
  }

  private createSharedLayer(environment: string): lambda.LayerVersion {
    const layerDir = 'lambda-layer';
    const layerCode = lambda.Code.fromAsset(layerDir);

    return new lambda.LayerVersion(this, 'SharedLayer', {
      layerVersionName: `lingible-shared-layer-${environment}`,
      code: layerCode,
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Shared code for Lingible Lambda functions',
    });
  }

  private createHandlerPackage(handlerPath: string): lambda.Code {
    // Create handler-specific package directory
    const handlerName = handlerPath.split('.').slice(-2, -1)[0]; // Extract handler name from path
    const packageDir = `lambda-packages/${handlerName}`;

    if (!fs.existsSync(packageDir)) {
      fs.mkdirSync(packageDir, { recursive: true });
    }

    // Copy only the specific handler code
    const handlerDir = `../src/handlers/${handlerName}`;
    if (fs.existsSync(handlerDir)) {
      this.copyDirectory(handlerDir, packageDir);
    }

    // Create __init__.py if it doesn't exist
    const initFile = `${packageDir}/__init__.py`;
    if (!fs.existsSync(initFile)) {
      fs.writeFileSync(initFile, '# Handler package\n');
    }

    return lambda.Code.fromAsset(packageDir);
  }

  private copyDirectory(src: string, dest: string): void {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }

    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
      const srcPath = path.join(src, entry.name);
      const destPath = path.join(dest, entry.name);

      if (entry.isDirectory()) {
        this.copyDirectory(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }

  private createLambdaFunctions(
    environment: string,
    commonEnv: any,
    lambdaConfig: any,
    lambdaPolicyStatements: iam.PolicyStatement[]
  ): void {
    // API Handlers
    this.authorizerLambda = new lambda.Function(this, 'AuthorizerLambda', {
      functionName: `lingible-authorizer-${environment}`,
      handler: 'authorizer.authorizer.lambda_handler',
      code: this.createHandlerPackage('src.handlers.authorizer.authorizer'),
      environment: {
        ...commonEnv,
        USER_POOL_ID: this.userPool.userPoolId,
        USER_POOL_CLIENT_ID: this.userPoolClient.userPoolClientId,
      },
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.authorizerLambda.addToRolePolicy(statement));

    this.translateLambda = new lambda.Function(this, 'TranslateLambda', {
      functionName: `lingible-translate-${environment}`,
      handler: 'translate_api_handler.handler',
      code: this.createHandlerPackage('src.handlers.translate_api.translate_api_handler'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.translateLambda.addToRolePolicy(statement));

    this.userProfileLambda = new lambda.Function(this, 'UserProfileLambda', {
      functionName: `lingible-user-profile-${environment}`,
      handler: 'user_profile_api_handler.handler',
      code: this.createHandlerPackage('src.handlers.user_profile_api.user_profile_api_handler'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.userProfileLambda.addToRolePolicy(statement));

    this.userUsageLambda = new lambda.Function(this, 'UserUsageLambda', {
      functionName: `lingible-user-usage-${environment}`,
      handler: 'user_usage_api_handler.handler',
      code: this.createHandlerPackage('src.handlers.user_usage_api.user_usage_api_handler'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.userUsageLambda.addToRolePolicy(statement));

    this.userUpgradeLambda = new lambda.Function(this, 'UserUpgradeLambda', {
      functionName: `lingible-user-upgrade-${environment}`,
      handler: 'user_upgrade_api_handler.handler',
      code: this.createHandlerPackage('src.handlers.user_upgrade_api.user_upgrade_api_handler'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.userUpgradeLambda.addToRolePolicy(statement));

    this.translationHistoryLambda = new lambda.Function(this, 'TranslationHistoryLambda', {
      functionName: `lingible-translation-history-${environment}`,
      handler: 'get_translation_history.handler',
      code: this.createHandlerPackage('src.handlers.translation_history_api.get_translation_history'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.translationHistoryLambda.addToRolePolicy(statement));

    this.deleteTranslationLambda = new lambda.Function(this, 'DeleteTranslationLambda', {
      functionName: `lingible-delete-translation-${environment}`,
      handler: 'delete_translation.handler',
      code: this.createHandlerPackage('src.handlers.translation_history_api.delete_translation'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.deleteTranslationLambda.addToRolePolicy(statement));

    this.deleteAllTranslationsLambda = new lambda.Function(this, 'DeleteAllTranslationsLambda', {
      functionName: `lingible-delete-all-translations-${environment}`,
      handler: 'delete_all_translations.handler',
      code: this.createHandlerPackage('src.handlers.translation_history_api.delete_all_translations'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.deleteAllTranslationsLambda.addToRolePolicy(statement));

    this.healthLambda = new lambda.Function(this, 'HealthLambda', {
      functionName: `lingible-health-${environment}`,
      handler: 'health_api_handler.handler',
      code: this.createHandlerPackage('src.handlers.health_api.health_api_handler'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.healthLambda.addToRolePolicy(statement));

    // Webhook Handlers
    this.appleWebhookLambda = new lambda.Function(this, 'AppleWebhookLambda', {
      functionName: `lingible-apple-webhook-${environment}`,
      handler: 'apple_webhook_handler.handler',
      code: this.createHandlerPackage('src.handlers.apple_webhook.apple_webhook_handler'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.appleWebhookLambda.addToRolePolicy(statement));

    // Cognito Triggers
    this.postConfirmationLambda = new lambda.Function(this, 'PostConfirmationLambda', {
      functionName: `lingible-post-confirmation-${environment}`,
      handler: 'cognito_post_confirmation.cognito_post_confirmation.lambda_handler',
      code: this.createHandlerPackage('src.handlers.cognito_post_confirmation.cognito_post_confirmation'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.postConfirmationLambda.addToRolePolicy(statement));

    this.preAuthenticationLambda = new lambda.Function(this, 'PreAuthenticationLambda', {
      functionName: `lingible-pre-authentication-${environment}`,
      handler: 'cognito_pre_authentication.cognito_pre_authentication.lambda_handler',
      code: this.createHandlerPackage('src.handlers.cognito_pre_authentication.cognito_pre_authentication'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.preAuthenticationLambda.addToRolePolicy(statement));

    this.preUserDeletionLambda = new lambda.Function(this, 'PreUserDeletionLambda', {
      functionName: `lingible-pre-user-deletion-${environment}`,
      handler: 'cognito_pre_user_deletion.cognito_pre_user_deletion.lambda_handler',
      code: this.createHandlerPackage('src.handlers.cognito_pre_user_deletion.cognito_pre_user_deletion'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.preUserDeletionLambda.addToRolePolicy(statement));

    // Background Processing
    this.userDataCleanupLambda = new lambda.Function(this, 'UserDataCleanupLambda', {
      functionName: `lingible-user-data-cleanup-${environment}`,
      handler: 'user_data_cleanup.user_data_cleanup.lambda_handler',
      code: this.createHandlerPackage('src.handlers.user_data_cleanup.user_data_cleanup'),
      environment: commonEnv,
      layers: [this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.userDataCleanupLambda.addToRolePolicy(statement));
  }

  private setupCognitoTriggers(): void {
    // Configure Cognito triggers
    this.userPool.addTrigger(
      cognito.UserPoolOperation.POST_CONFIRMATION,
      this.postConfirmationLambda,
    );

    this.userPool.addTrigger(
      cognito.UserPoolOperation.PRE_AUTHENTICATION,
      this.preAuthenticationLambda,
    );

    // Note: PRE_USER_DELETION is not available in the current CDK version
    // this.userPool.addTrigger(
    //   cognito.UserPoolOperation.PRE_USER_DELETION,
    //   this.preUserDeletionLambda,
    // );

    // Grant Cognito permission to invoke Lambda functions
    this.postConfirmationLambda.addPermission('CognitoPostConfirmation', {
      principal: new iam.ServicePrincipal('cognito-idp.amazonaws.com'),
      sourceArn: this.userPool.userPoolArn,
    });

    this.preAuthenticationLambda.addPermission('CognitoPreAuthentication', {
      principal: new iam.ServicePrincipal('cognito-idp.amazonaws.com'),
      sourceArn: this.userPool.userPoolArn,
    });

    this.preUserDeletionLambda.addPermission('CognitoPreUserDeletion', {
      principal: new iam.ServicePrincipal('cognito-idp.amazonaws.com'),
      sourceArn: this.userPool.userPoolArn,
    });
  }

  private createApiGateway(environment: string, hostedZone: route53.IHostedZone): void {
    // Create SSL certificate
    this.certificate = new acm.Certificate(this, 'ApiCertificate', {
      domainName: `api.${environment}.lingible.com`,
      validation: acm.CertificateValidation.fromDns(),
    });

    // Create API Gateway
    this.api = new apigateway.RestApi(this, 'LingibleApi', {
      restApiName: `lingible-api-${environment}`,
      description: `Lingible API for ${environment} environment`,
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: apigateway.Cors.DEFAULT_HEADERS,
      },
      domainName: {
        domainName: `api.${environment}.lingible.com`,
        certificate: this.certificate,
      },
    });

    // Create custom authorizer
    const authorizer = new apigateway.TokenAuthorizer(this, 'CognitoAuthorizer', {
      handler: this.authorizerLambda,
      identitySource: 'method.request.header.Authorization',
    });

    // Create API models
    const errorModel = this.api.addModel('ErrorModel', {
      contentType: 'application/json',
      modelName: 'Error',
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
      modelName: 'Success',
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          message: { type: apigateway.JsonSchemaType.STRING },
          data: { type: apigateway.JsonSchemaType.OBJECT },
        },
      },
    });

    // Create API resources and methods
    this.createApiResources(authorizer, errorModel, successModel);

    // Create DNS record
    new route53.ARecord(this, 'ApiAliasRecord', {
      zone: hostedZone,
      recordName: `api.${environment}`,
      target: route53.RecordTarget.fromAlias(
        new targets.ApiGateway(this.api)
      ),
    });
  }

  private createApiResources(
    authorizer: apigateway.TokenAuthorizer,
    errorModel: apigateway.Model,
    successModel: apigateway.Model
  ): void {
    // Health endpoint (no auth required)
    const health = this.api.root.addResource('health');
    health.addMethod('GET', new apigateway.LambdaIntegration(this.healthLambda), {
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
      ],
    });

    // API v1
    const v1 = this.api.root.addResource('v1');

    // Translate endpoint
    const translate = v1.addResource('translate');
    translate.addMethod('POST', new apigateway.LambdaIntegration(this.translateLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // User profile endpoints
    const user = v1.addResource('user');
    const profile = user.addResource('profile');
    profile.addMethod('GET', new apigateway.LambdaIntegration(this.userProfileLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // User usage endpoint
    const usage = user.addResource('usage');
    usage.addMethod('GET', new apigateway.LambdaIntegration(this.userUsageLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // User upgrade endpoint
    const upgrade = user.addResource('upgrade');
    upgrade.addMethod('POST', new apigateway.LambdaIntegration(this.userUpgradeLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // Translation history endpoints
    const translations = v1.addResource('translations');
    translations.addMethod('GET', new apigateway.LambdaIntegration(this.translationHistoryLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    const translationId = translations.addResource('{translationId}');
    translationId.addMethod('DELETE', new apigateway.LambdaIntegration(this.deleteTranslationLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // Delete all translations endpoint
    const deleteAll = translations.addResource('delete-all');
    deleteAll.addMethod('DELETE', new apigateway.LambdaIntegration(this.deleteAllTranslationsLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // Apple webhook endpoint (no auth required)
    const webhook = this.api.root.addResource('webhook');
    const apple = webhook.addResource('apple');
    apple.addMethod('POST', new apigateway.LambdaIntegration(this.appleWebhookLambda), {
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
      ],
    });
  }

  private createMonitoring(environment: string): void {
    // Create SNS topic for alerts
    this.alertTopic = new sns.Topic(this, 'AlertTopic', {
      topicName: `lingible-alerts-${environment}`,
      displayName: `Lingible ${environment} Alerts`,
    });

    // Create CloudWatch Dashboard
    this.dashboard = new cloudwatch.Dashboard(this, 'LingibleDashboard', {
      dashboardName: `Lingible-${environment}`,
    });

    // Add Lambda metrics
    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Invocations',
        left: [
          this.translateLambda.metricInvocations(),
          this.userProfileLambda.metricInvocations(),
          this.translationHistoryLambda.metricInvocations(),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Errors',
        left: [
          this.translateLambda.metricErrors(),
          this.userProfileLambda.metricErrors(),
          this.translationHistoryLambda.metricErrors(),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration',
        left: [
          this.translateLambda.metricDuration(),
          this.userProfileLambda.metricDuration(),
          this.translationHistoryLambda.metricDuration(),
        ],
      })
    );

    // Add API Gateway metrics
    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Gateway Requests',
        left: [this.api.metricCount()],
      })
    );

    // Add DynamoDB metrics
    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'DynamoDB Read Capacity',
        left: [
          this.usersTable.metricConsumedReadCapacityUnits(),
          this.translationsTable.metricConsumedReadCapacityUnits(),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'DynamoDB Write Capacity',
        left: [
          this.usersTable.metricConsumedWriteCapacityUnits(),
          this.translationsTable.metricConsumedWriteCapacityUnits(),
        ],
      })
    );

    // Create alarms
    new cloudwatch.Alarm(this, 'HighLambdaErrors', {
      metric: this.translateLambda.metricErrors(),
      threshold: 10,
      evaluationPeriods: 2,
      alarmDescription: 'High Lambda error rate',
    }).addAlarmAction(new actions.SnsAction(this.alertTopic));
  }

  private createOutputs(environment: string): void {
    // Database outputs
    new CfnOutput(this, 'UsersTableName', {
      value: this.usersTable.tableName,
      description: 'Users DynamoDB table name',
      exportName: `Lingible-${environment}-UsersTableName`,
    });

    new CfnOutput(this, 'TranslationsTableName', {
      value: this.translationsTable.tableName,
      description: 'Translations DynamoDB table name',
      exportName: `Lingible-${environment}-TranslationsTableName`,
    });

    // Cognito outputs
    new CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `Lingible-${environment}-UserPoolId`,
    });

    new CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
      exportName: `Lingible-${environment}-UserPoolClientId`,
    });

    new CfnOutput(this, 'UserPoolArn', {
      value: this.userPool.userPoolArn,
      description: 'Cognito User Pool ARN',
      exportName: `Lingible-${environment}-UserPoolArn`,
    });

    // API Gateway outputs
    new CfnOutput(this, 'ApiUrl', {
      value: this.api.url,
      description: 'API Gateway URL',
      exportName: `Lingible-${environment}-ApiUrl`,
    });

    new CfnOutput(this, 'ApiDomainName', {
      value: `api.${environment}.lingible.com`,
      description: 'API Gateway custom domain name',
      exportName: `Lingible-${environment}-ApiDomainName`,
    });

    // Monitoring outputs
    new CfnOutput(this, 'DashboardName', {
      value: this.dashboard.dashboardName,
      description: 'CloudWatch Dashboard name',
      exportName: `Lingible-${environment}-DashboardName`,
    });

    new CfnOutput(this, 'AlertTopicArn', {
      value: this.alertTopic.topicArn,
      description: 'SNS Alert Topic ARN',
      exportName: `Lingible-${environment}-AlertTopicArn`,
    });
  }
}
