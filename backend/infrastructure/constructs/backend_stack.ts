import * as cdk from 'aws-cdk-lib';
import { Stack } from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as events from 'aws-cdk-lib/aws-events';
import * as eventTargets from 'aws-cdk-lib/aws-events-targets';

import { Duration, RemovalPolicy, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as path from 'path';
import { ConfigLoader } from '../utils/config-loader';

export class BackendStack extends Construct {
  // Database resources
  public usersTable!: dynamodb.Table;
  public translationsTable!: dynamodb.Table;
  public trendingTable!: dynamodb.Table;

  // Cognito resources
  public userPool!: cognito.UserPool;
  public userPoolClient!: cognito.UserPoolClient;
  public appleProvider!: cognito.UserPoolIdentityProviderApple;

  // Lambda layers
  public sharedLayer!: lambda.LayerVersion;
  public dependenciesLayer!: lambda.LayerVersion;

  // Lambda functions
  public authorizerLambda!: lambda.Function;
  public translateLambda!: lambda.Function;
  public userProfileLambda!: lambda.Function;
  public userUsageLambda!: lambda.Function;
  public userUpgradeLambda!: lambda.Function;
  public userAccountDeletionLambda!: lambda.Function;
  public translationHistoryLambda!: lambda.Function;
  public deleteTranslationLambda!: lambda.Function;
  public deleteAllTranslationsLambda!: lambda.Function;
  public healthLambda!: lambda.Function;
  public appleWebhookLambda!: lambda.Function;
  public postConfirmationLambda!: lambda.Function;
  public trendingLambda!: lambda.Function;
  public trendingJobLambda!: lambda.Function;

  // Configuration loader
  private configLoader!: ConfigLoader;
  private environment!: string;
  public userDataCleanupLambda!: lambda.Function;

  // API Gateway resources
  public api!: apigateway.RestApi;
  public certificate!: acm.Certificate;
  public apiDomainName!: string;

  // Cognito custom domain resources
  public authCertificate!: acm.Certificate;
  public authDomainName!: string;

  // Monitoring resources
  public dashboard!: cloudwatch.Dashboard;
  public alertTopic!: sns.Topic;

  constructor(
    scope: Construct,
    id: string,
    props: {
      environment: string;
      hostedZone: route53.IHostedZone;
      appleClientId?: string;
      appleTeamId?: string;
      appleKeyId?: string;
    }
  ) {
    super(scope, id);

    const { environment, hostedZone, appleClientId, appleTeamId, appleKeyId } = props;

    // Load configuration from shared config files
    this.configLoader = new ConfigLoader(path.resolve(__dirname, '../../..'));
    this.environment = environment;
    const config = this.configLoader.getMergedConfig(environment);
    const backendConfig = this.configLoader.loadBackendConfig(environment);

    // Create Lambda layers
    this.dependenciesLayer = this.createDependenciesLayer(environment);
    this.sharedLayer = this.createSharedLayer(environment);

    // Create DynamoDB tables
    this.createDatabaseTables(environment,
      { name: config.tables.users_table.name, read_capacity: 5, write_capacity: 5 },
      { name: config.tables.translations_table.name, read_capacity: 5, write_capacity: 5 },
      { name: config.tables.trending_table.name, read_capacity: 5, write_capacity: 5 }
    );
    const lambdaConfig = {
      runtime: lambda.Runtime.PYTHON_3_13,
      timeout: Duration.seconds(30),
      memorySize: 512,
      logRetention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      architecture: lambda.Architecture.ARM_64, // ARM64 Graviton2
    };

    // Environment variables are now inlined in each Lambda function
    const baseEnvironmentVariables ={
        // Environment
        ENVIRONMENT: environment,

        // AWS Resources
        USERS_TABLE: config.tables.users_table.name,
        TRANSLATIONS_TABLE: config.tables.translations_table.name,
        TRENDING_TABLE: config.tables.trending_table.name,

        // Bedrock Config
        BEDROCK_MODEL: backendConfig.bedrock.model,
        BEDROCK_MAX_TOKENS: backendConfig.bedrock.max_tokens.toString(),
        BEDROCK_TEMPERATURE: backendConfig.bedrock.temperature.toString(),

        // Usage Limits
        FREE_DAILY_TRANSLATIONS: backendConfig.limits.free_daily_translations.toString(),
        PREMIUM_DAILY_TRANSLATIONS: backendConfig.limits.premium_daily_translations.toString(),
        FREE_MAX_TEXT_LENGTH: backendConfig.limits.free_max_text_length.toString(),
        PREMIUM_MAX_TEXT_LENGTH: backendConfig.limits.premium_max_text_length.toString(),
        FREE_HISTORY_RETENTION_DAYS: backendConfig.limits.free_history_retention_days.toString(),
        PREMIUM_HISTORY_RETENTION_DAYS: backendConfig.limits.premium_history_retention_days.toString(),

        // Security Config
        SENSITIVE_FIELD_PATTERNS: JSON.stringify(backendConfig.security.sensitive_field_patterns),

        // Observability Config
        LOG_LEVEL: backendConfig.observability.log_level,
        ENABLE_TRACING: backendConfig.observability.enable_tracing.toString(),
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
          this.trendingTable.tableArn,
          `${this.usersTable.tableArn}/index/*`,
          `${this.translationsTable.tableArn}/index/*`,
          `${this.trendingTable.tableArn}/index/*`,
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

    // Create certificates for custom domains
    this.createCertificates(environment, hostedZone);

    // Create Cognito User Pool
    this.createCognitoUserPool(environment, hostedZone, appleClientId, appleTeamId, appleKeyId);

    // Create Lambda functions
    this.createLambdaFunctions(environment, lambdaConfig, lambdaPolicyStatements, baseEnvironmentVariables);

    // Configure Cognito triggers (after Lambda functions are created)
    this.setupCognitoTriggers();

    // Create API Gateway
    this.createApiGateway(environment, hostedZone);



    // Create scheduled jobs
    this.createScheduledJobs(environment, backendConfig);

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

  private createDatabaseTables(
    environment: string,
    usersTableConfig: { name: string; read_capacity: number; write_capacity: number },
    translationsTableConfig: { name: string; read_capacity: number; write_capacity: number },
    trendingTableConfig: { name: string; read_capacity: number; write_capacity: number }
  ): void {
    // Users table
    this.usersTable = new dynamodb.Table(this, 'UsersTable', {
      tableName: usersTableConfig.name,
      partitionKey: {
        name: 'PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'SK',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      pointInTimeRecovery: true,
    });

    // Translations table
    this.translationsTable = new dynamodb.Table(this, 'TranslationsTable', {
      tableName: translationsTableConfig.name,
      partitionKey: {
        name: 'PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'SK',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      pointInTimeRecovery: true,
    });

    // Trending table
    this.trendingTable = new dynamodb.Table(this, 'TrendingTable', {
      tableName: trendingTableConfig.name,
      partitionKey: {
        name: 'PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'SK',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      pointInTimeRecovery: true,
    });

    // Add GSI for trending terms by popularity
    this.trendingTable.addGlobalSecondaryIndex({
      indexName: 'PopularityIndex',
      partitionKey: {
        name: 'is_active',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'popularity_score',
        type: dynamodb.AttributeType.NUMBER,
      },
    });

    // Add GSI for trending terms by category
    this.trendingTable.addGlobalSecondaryIndex({
      indexName: 'CategoryPopularityIndex',
      partitionKey: {
        name: 'category',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'popularity_score',
        type: dynamodb.AttributeType.NUMBER,
      },
    });

  }

  private createCertificates(environment: string, hostedZone: route53.IHostedZone): void {
    // Create SSL certificate for API Gateway
    this.apiDomainName = environment === 'prod' ? 'api.lingible.com' : `api.${environment}.lingible.com`;
    this.certificate = new acm.Certificate(this, 'ApiCertificate', {
      domainName: this.apiDomainName,
      validation: acm.CertificateValidation.fromDns(),
    });

    // Create SSL certificate for Cognito custom domain
    this.authDomainName = environment === 'prod' ? 'auth.lingible.com' : `auth.${environment}.lingible.com`;
    this.authCertificate = new acm.Certificate(this, 'AuthCertificate', {
      domainName: this.authDomainName,
      validation: acm.CertificateValidation.fromDns(),
    });
  }

  private createCognitoUserPool(
    environment: string,
    hostedZone: route53.IHostedZone,
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
    this.appleProvider = new cognito.UserPoolIdentityProviderApple(this, 'AppleProvider', {
      userPool: this.userPool,
      clientId: appleClientId || 'TO_BE_SET',
      teamId: appleTeamId || 'TO_BE_SET',
      keyId: appleKeyId || 'TO_BE_SET',
      privateKeyValue: cdk.SecretValue.secretsManager(`lingible-apple-private-key-${environment}`, {
        jsonField: 'privateKey',
      }),
      scopes: ['openid', 'email', 'name'],
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
          cognito.OAuthScope.OPENID,  // Required for OAuth flows
          cognito.OAuthScope.EMAIL,   // Required for user identification
          cognito.OAuthScope.PROFILE, // Required for Apple Sign In

        ],
        callbackUrls: [
          environment === 'dev'
            ? 'com.lingible.lingible.dev://auth/callback'
            : 'com.lingible.lingible://auth/callback', // For iOS app
        ],
        logoutUrls: [
          environment === 'dev'
            ? 'com.lingible.lingible.dev://auth/logout'
            : 'com.lingible.lingible://auth/logout', // For iOS app
        ],
        // Note: Cognito domain is now managed (not custom)
        // OAuth endpoints: https://lingible-dev.auth.us-east-1.amazoncognito.com
      },
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.APPLE,
      ],
      preventUserExistenceErrors: true,
    });

    // Ensure Apple provider is created before User Pool Client
    this.userPoolClient.node.addDependency(this.appleProvider);

    // Add User Pool Domain for OAuth endpoints (Custom Domain)
    const userPoolDomain = new cognito.UserPoolDomain(this, 'LingibleUserPoolDomain', {
      userPool: this.userPool,
      customDomain: {
        domainName: this.authDomainName,
        certificate: this.authCertificate,
      },
    });

    // Add CNAME record for Cognito custom domain (dev only - prod requires manual Squarespace setup)
    if (environment !== 'prod') {
      new route53.CnameRecord(this, 'AuthDomainCnameRecord', {
        zone: hostedZone,
        recordName: this.authDomainName,
        domainName: userPoolDomain.cloudFrontDomainName,
      });
    }

    // Note: Using custom domain for better branding and user experience
    // Custom domain format: https://auth.dev.lingible.com (dev) or https://auth.lingible.com (prod)
    // Dev: CNAME record created automatically via Route 53
    // Prod: Manual CNAME record required in Squarespace DNS pointing to CloudFront domain
  }

  private createDependenciesLayer(environment: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, 'DependenciesLayer', {
      layerVersionName: `lingible-dependencies-layer-${environment}`,
      code: lambda.Code.fromAsset('../lambda', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          platform: 'linux/arm64',
          command: [
            'bash', '-c',
            'rm -rf /asset-output/python && pip install --platform manylinux2014_aarch64 --implementation cp --python-version 3.13 --only-binary=:all: --upgrade --target /asset-output/python -r requirements.txt'
          ],
        },
        // Only redeploy requirements layer when requirements.txt changes
        assetHashType: cdk.AssetHashType.SOURCE,
        exclude: [
          '**/*',
          '!requirements.txt',
          '**/__pycache__/**',
          '**/*.pyc',
          '**/*.pyo',
          '**/*.pyd',
          '**/.pytest_cache/**',
          '**/.coverage',
          '**/.mypy_cache/**'
        ]
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Python dependencies for Lingible Lambda functions',
    });
  }

  private createSharedLayer(environment: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, 'SharedLayer', {
      layerVersionName: `lingible-shared-layer-${environment}`,
      description: `Shared services, repositories, and models for Lingible Lambda functions`,
      code: lambda.Code.fromAsset('./lambda-layer', {
        exclude: [
          '**/__pycache__/**',
          '**/*.pyc',
          '**/*.pyo',
          '**/*.pyd',
          '**/.pytest_cache/**',
          '**/.coverage',
          '**/.mypy_cache/**',
        ]
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
    });
  }

  private createHandlerPackage(handlerPath: string): lambda.Code {
    // Extract handler name from the handler path
    // handlerPath format: 'src.handlers.translate_api.translate_api_handler' -> handlerName = 'translate_api'
    const pathParts = handlerPath.split('.');
    const handlerName = pathParts[pathParts.length - 2]; // e.g., "translate_api", "health_api", etc.

    // Determine the actual Python file name based on the handler directory
    let pythonFileName: string;
    pythonFileName = `handler.py`;

    // Simple approach: bundle from individual handler directories
    return lambda.Code.fromAsset(`../lambda/src/handlers/${handlerName}`, {
      bundling: {
        image: lambda.Runtime.PYTHON_3_13.bundlingImage,
        platform: 'linux/arm64',
        command: [
          'bash', '-c',
          `cp ${pythonFileName} /asset-output/`
        ]
      },
      exclude: [
        '**/__pycache__/**',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',
        '**/.pytest_cache/**',
        '**/.coverage',
        '**/.mypy_cache/**'
      ]
    });
  }




  private getEnvironmentVariables(environment: string, config: any, backendConfig: any): { [key: string]: string } {
    return {
      // Environment
      ENVIRONMENT: environment,

      // AWS Resources
      USERS_TABLE: config.tables.users_table.name,
      TRANSLATIONS_TABLE: config.tables.translations_table.name,
      TRENDING_TABLE: config.tables.trending_table.name,

      // Bedrock Config
      BEDROCK_MODEL: backendConfig.bedrock.model,
      BEDROCK_MAX_TOKENS: backendConfig.bedrock.max_tokens.toString(),
      BEDROCK_TEMPERATURE: backendConfig.bedrock.temperature.toString(),

      // Usage Limits
      FREE_DAILY_TRANSLATIONS: backendConfig.limits.free_daily_translations.toString(),
      PREMIUM_DAILY_TRANSLATIONS: backendConfig.limits.premium_daily_translations.toString(),
      FREE_MAX_TEXT_LENGTH: backendConfig.limits.free_max_text_length.toString(),
      PREMIUM_MAX_TEXT_LENGTH: backendConfig.limits.premium_max_text_length.toString(),
      FREE_HISTORY_RETENTION_DAYS: backendConfig.limits.free_history_retention_days.toString(),
      PREMIUM_HISTORY_RETENTION_DAYS: backendConfig.limits.premium_history_retention_days.toString(),

      // Security Config
      SENSITIVE_FIELD_PATTERNS: JSON.stringify(backendConfig.security.sensitive_field_patterns),

      // Observability Config
      LOG_LEVEL: backendConfig.observability.log_level,
      ENABLE_TRACING: backendConfig.observability.enable_tracing.toString(),
    };
  }

  private createLambdaFunctions(
    environment: string,
    lambdaConfig: any,
    lambdaPolicyStatements: iam.PolicyStatement[],
    baseEnvironmentVariables: { [key: string]: string }
  ): void {
    // API Handlers
    const config = this.configLoader.getMergedConfig(environment);
    const backendConfig = this.configLoader.loadBackendConfig(environment);

    this.authorizerLambda = new lambda.Function(this, 'AuthorizerLambda', {
      functionName: `lingible-authorizer-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.authorizer.authorizer'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-authorizer',
        ...baseEnvironmentVariables,
        COGNITO_USER_POOL_ID: this.userPool.userPoolId,
        COGNITO_USER_POOL_CLIENT_ID: this.userPoolClient.userPoolClientId,
        COGNITO_USER_POOL_REGION: config.aws.region,
        API_GATEWAY_ARN: `arn:aws:execute-api:${config.aws.region}:${Stack.of(this).account}:*/*`,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 384,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.authorizerLambda.addToRolePolicy(statement));

    this.translateLambda = new lambda.Function(this, 'TranslateLambda', {
      functionName: `lingible-translate-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.translate_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-translate',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 512,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.translateLambda.addToRolePolicy(statement));

    // Add Bedrock permissions for translation Lambda
    this.translateLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
      ],
      resources: [
        `arn:aws:bedrock:${config.bedrock.region}::foundation-model/${backendConfig.bedrock.model}`,
      ],
    }));

    this.userProfileLambda = new lambda.Function(this, 'UserProfileLambda', {
      functionName: `lingible-user-profile-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_profile_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-user-profile',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.userProfileLambda.addToRolePolicy(statement));

    this.userUsageLambda = new lambda.Function(this, 'UserUsageLambda', {
      functionName: `lingible-user-usage-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_usage_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-user-usage',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.userUsageLambda.addToRolePolicy(statement));

    this.userUpgradeLambda = new lambda.Function(this, 'UserUpgradeLambda', {
      functionName: `lingible-user-upgrade-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_upgrade_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-user-upgrade',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 384,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.userUpgradeLambda.addToRolePolicy(statement));

    // Add secrets permissions for receipt validation
    this.userUpgradeLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-shared-secret-${environment}*`,
        `arn:aws:secretsmanager:*:*:secret:lingible-google-service-account-${environment}*`,
      ],
    }));

    this.userAccountDeletionLambda = new lambda.Function(this, 'UserAccountDeletionLambda', {
      functionName: `lingible-user-account-deletion-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_account_deletion.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-user-account-deletion',
        ...baseEnvironmentVariables,
        COGNITO_USER_POOL_ID: this.userPool.userPoolId,
        COGNITO_USER_POOL_CLIENT_ID: this.userPoolClient.userPoolClientId,
        COGNITO_USER_POOL_REGION: config.aws.region,
        API_GATEWAY_ARN: `arn:aws:execute-api:${config.aws.region}:${Stack.of(this).account}:*/*`,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 384,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.userAccountDeletionLambda.addToRolePolicy(statement));

    // Add secrets permissions for receipt validation
    this.userAccountDeletionLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-shared-secret-${environment}*`,
        `arn:aws:secretsmanager:*:*:secret:lingible-google-service-account-${environment}*`,
      ],
    }));

    // Add Cognito permissions for user account deletion
    this.userAccountDeletionLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cognito-idp:AdminDeleteUser',
      ],
      resources: [
        this.userPool.userPoolArn,
      ],
    }));

    this.translationHistoryLambda = new lambda.Function(this, 'TranslationHistoryLambda', {
      functionName: `lingible-translation-history-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.get_translation_history.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-translation-history',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.translationHistoryLambda.addToRolePolicy(statement));

    this.deleteTranslationLambda = new lambda.Function(this, 'DeleteTranslationLambda', {
      functionName: `lingible-delete-translation-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.delete_translation.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-delete-translation',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.deleteTranslationLambda.addToRolePolicy(statement));

    this.deleteAllTranslationsLambda = new lambda.Function(this, 'DeleteAllTranslationsLambda', {
      functionName: `lingible-delete-all-translations-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.delete_translations.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-delete-all-translations',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.deleteAllTranslationsLambda.addToRolePolicy(statement));

    this.healthLambda = new lambda.Function(this, 'HealthLambda', {
      functionName: `lingible-health-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.health_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-health',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 128,
      timeout: Duration.seconds(10),
    });
    lambdaPolicyStatements.forEach(statement => this.healthLambda.addToRolePolicy(statement));

    this.trendingLambda = new lambda.Function(this, 'TrendingLambda', {
      functionName: `lingible-trending-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.trending_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-trending',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.trendingLambda.addToRolePolicy(statement));

    // Webhook Handlers
    this.appleWebhookLambda = new lambda.Function(this, 'AppleWebhookLambda', {
      functionName: `lingible-apple-webhook-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.apple_webhook.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-apple-webhook',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 384,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.appleWebhookLambda.addToRolePolicy(statement));

    // Add secrets permissions for receipt validation
    this.appleWebhookLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-shared-secret-${environment}*`,
        `arn:aws:secretsmanager:*:*:secret:lingible-google-service-account-${environment}*`,
      ],
    }));

    // Cognito Triggers
    this.postConfirmationLambda = new lambda.Function(this, 'PostConfirmationLambda', {
      functionName: `lingible-post-confirmation-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.cognito_post_confirmation.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-post-confirmation',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.postConfirmationLambda.addToRolePolicy(statement));



    // Background Processing
    this.userDataCleanupLambda = new lambda.Function(this, 'UserDataCleanupLambda', {
      functionName: `lingible-user-data-cleanup-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_data_cleanup.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-user-data-cleanup',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(60),
    });
    lambdaPolicyStatements.forEach(statement => this.userDataCleanupLambda.addToRolePolicy(statement));

    // Add secrets permissions for receipt validation
    this.userDataCleanupLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-shared-secret-${environment}*`,
        `arn:aws:secretsmanager:*:*:secret:lingible-google-service-account-${environment}*`,
      ],
    }));

    this.trendingJobLambda = new lambda.Function(this, 'TrendingJobLambda', {
      functionName: `lingible-trending-job-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.trending_job.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-trending-job',
        ...baseEnvironmentVariables,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(60),
    });
    lambdaPolicyStatements.forEach(statement => this.trendingJobLambda.addToRolePolicy(statement));
  }

  private setupCognitoTriggers(): void {
    // Configure Cognito triggers
    this.userPool.addTrigger(
      cognito.UserPoolOperation.POST_CONFIRMATION,
      this.postConfirmationLambda,
    );



    // Grant Cognito permission to invoke Lambda functions
    this.postConfirmationLambda.addPermission('CognitoPostConfirmation', {
      principal: new iam.ServicePrincipal('cognito-idp.amazonaws.com'),
      sourceArn: this.userPool.userPoolArn,
    });


  }

  private grantApiGatewayPermissions(): void {
    // Grant API Gateway permission to invoke Lambda functions
    this.healthLambda.addPermission('ApiGatewayHealth', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.trendingLambda.addPermission('ApiGatewayTrending', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.translateLambda.addPermission('ApiGatewayTranslate', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.userProfileLambda.addPermission('ApiGatewayUserProfile', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.userUsageLambda.addPermission('ApiGatewayUserUsage', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.userUpgradeLambda.addPermission('ApiGatewayUserUpgrade', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.userAccountDeletionLambda.addPermission('ApiGatewayUserAccountDeletion', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.translationHistoryLambda.addPermission('ApiGatewayTranslationHistory', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.deleteTranslationLambda.addPermission('ApiGatewayDeleteTranslation', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.deleteAllTranslationsLambda.addPermission('ApiGatewayDeleteAllTranslations', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });

    this.appleWebhookLambda.addPermission('ApiGatewayAppleWebhook', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:${this.api.restApiId}/*`,
    });
  }

  private createApiGateway(environment: string, hostedZone: route53.IHostedZone): void {
    // SSL certificate is created in createCertificates method

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
        domainName: this.apiDomainName,
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

    // Create API resources and methods
    this.createApiResources(authorizer, errorModel, successModel);

    // Grant API Gateway permission to invoke Lambda functions
    this.grantApiGatewayPermissions();

    // Create DNS record
    new route53.ARecord(this, 'ApiAliasRecord', {
      zone: hostedZone,
      recordName: `api`,
      target: route53.RecordTarget.fromAlias(
        new route53Targets.ApiGateway(this.api)
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

    // Translate endpoint
    const translate = this.api.root.addResource('translate');
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
    const user = this.api.root.addResource('user');
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

    // User account deletion endpoint
    const account = user.addResource('account');
    account.addMethod('DELETE', new apigateway.LambdaIntegration(this.userAccountDeletionLambda), {
      authorizer: authorizer,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': successModel,
          },
        },
        {
          statusCode: '400',
          responseModels: {
            'application/json': errorModel,
          },
        },
        {
          statusCode: '401',
          responseModels: {
            'application/json': errorModel,
          },
        },
        {
          statusCode: '500',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // Translation history endpoints
    const translations = this.api.root.addResource('translations');
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

    // Trending terms endpoint
    const trending = this.api.root.addResource('trending');
    trending.addMethod('GET', new apigateway.LambdaIntegration(this.trendingLambda), {
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

  private createScheduledJobs(environment: string, backendConfig: any): void {
    // Create EventBridge rule for trending job (daily at 6 AM UTC)
    const trendingJobRule = new events.Rule(this, 'TrendingJobSchedule', {
      ruleName: `lingible-trending-job-schedule-${environment}`,
      description: 'Daily schedule for trending terms generation',
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '6',
        day: '*',
        month: '*',
        year: '*',
      }),
    });

    // Add the trending job Lambda as a target
    trendingJobRule.addTarget(new eventTargets.LambdaFunction(this.trendingJobLambda, {
      event: events.RuleTargetInput.fromObject({
        job_type: 'gen_z_slang_analysis',
        source: 'bedrock_ai',
        parameters: {
          model: backendConfig.bedrock.model,
          max_terms: 20,
          categories: ['slang', 'meme', 'expression', 'hashtag', 'phrase'],
        },
      }),
    }));

    // Grant EventBridge permission to invoke the Lambda
    this.trendingJobLambda.addPermission('EventBridgeTrendingJob', {
      principal: new iam.ServicePrincipal('events.amazonaws.com'),
      sourceArn: trendingJobRule.ruleArn,
    });

    // Create a manual trigger rule for testing (can be removed in production)
    const manualTrendingJobRule = new events.Rule(this, 'ManualTrendingJobTrigger', {
      ruleName: `lingible-manual-trending-job-${environment}`,
      description: 'Manual trigger for trending terms generation (for testing)',
      eventPattern: {
        source: ['lingible.manual'],
        detailType: ['Trending Job Request'],
      },
    });

    manualTrendingJobRule.addTarget(new eventTargets.LambdaFunction(this.trendingJobLambda, {
      event: events.RuleTargetInput.fromObject({
        job_type: 'gen_z_slang_analysis',
        source: 'bedrock_ai',
        parameters: {
          model: backendConfig.bedrock.model,
          max_terms: 20,
          categories: ['slang', 'meme', 'expression', 'hashtag', 'phrase'],
        },
      }),
    }));

    this.trendingJobLambda.addPermission('EventBridgeManualTrendingJob', {
      principal: new iam.ServicePrincipal('events.amazonaws.com'),
      sourceArn: manualTrendingJobRule.ruleArn,
    });
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
      value: this.apiDomainName,
      description: 'API Gateway custom domain name',
      exportName: `Lingible-${environment}-ApiDomainName`,
    });

    new CfnOutput(this, 'AuthDomainName', {
      value: this.authDomainName,
      description: 'Cognito custom domain name for OAuth',
      exportName: `Lingible-${environment}-AuthDomainName`,
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
