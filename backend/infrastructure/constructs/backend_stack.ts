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
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as events from 'aws-cdk-lib/aws-events';
import * as eventTargets from 'aws-cdk-lib/aws-events-targets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';

import { Duration, RemovalPolicy, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as path from 'path';
import { ConfigLoader } from '../utils/config-loader';

export class BackendStack extends Construct {
  // Database resources
  public usersTable!: dynamodb.Table;
  public translationsTable!: dynamodb.Table;
  public trendingTable!: dynamodb.Table;
  public slangTermsTable!: dynamodb.Table;

  // S3 resources
  public lexiconBucket!: s3.Bucket;

  // Cognito resources
  public userPool!: cognito.UserPool;
  public userPoolClient!: cognito.UserPoolClient;
  public appleProvider!: cognito.UserPoolIdentityProviderApple;

  // Lambda layers
  public sharedLayer!: lambda.LayerVersion;
  public coreLayer!: lambda.LayerVersion;
  public receiptValidationLayer!: lambda.LayerVersion;
  public slangValidationLayer!: lambda.LayerVersion;

  // Lambda functions
  public translateLambda!: lambda.Function;
  public translateAlias?: lambda.CfnAlias;
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
  public submitSlangLambda!: lambda.Function;
  public slangUpvoteLambda!: lambda.Function;
  public slangPendingLambda!: lambda.Function;
  public slangAdminApproveLambda!: lambda.Function;
  public slangAdminRejectLambda!: lambda.Function;
  public slangValidationProcessorLambda!: lambda.Function;
  public exportLexiconLambda!: lambda.Function;
  public quizChallengeLambda!: lambda.Function;
  public quizSubmitLambda!: lambda.Function;
  public quizHistoryLambda!: lambda.Function;

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
  public slangSubmissionsTopic!: sns.Topic;
  public slangValidationRequestTopic!: sns.Topic;

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
    this.coreLayer = this.createCoreLayer(environment);
    this.receiptValidationLayer = this.createReceiptValidationLayer(environment);
    this.slangValidationLayer = this.createSlangValidationLayer(environment);
    this.sharedLayer = this.createSharedLayer(environment);

    // Create DynamoDB tables
    this.createDatabaseTables(
      { name: config.tables.users_table.name, read_capacity: 5, write_capacity: 5 },
      { name: config.tables.translations_table.name, read_capacity: 5, write_capacity: 5 },
      { name: config.tables.trending_table.name, read_capacity: 5, write_capacity: 5 },
      { name: config.tables.slang_submissions_table.name, read_capacity: 5, write_capacity: 5 }
    );

    // Create S3 bucket for lexicon
    this.createLexiconBucket(backendConfig.lexicon.s3_bucket);

    // Create SNS topics (needed for Lambda functions)
    this.createSnsTopics(environment);

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
        SLANG_TERMS_TABLE: config.tables.slang_submissions_table.name,

        // LLM Config
        LLM_MODEL_ID: backendConfig.llm.model,
        LLM_MAX_TOKENS: backendConfig.llm.max_tokens.toString(),
        LLM_TEMPERATURE: backendConfig.llm.temperature.toString(),
        LLM_TOP_P: backendConfig.llm.top_p.toString(),
        LLM_LOW_CONFIDENCE_THRESHOLD: backendConfig.llm.low_confidence_threshold.toString(),

        // Lexicon Config
        LEXICON_S3_BUCKET: backendConfig.lexicon.s3_bucket,
        LEXICON_S3_KEY: backendConfig.lexicon.s3_key,

        // Age Filtering
        AGE_MAX_RATING: backendConfig.age_filtering.max_rating,
        AGE_FILTER_MODE: backendConfig.age_filtering.filter_mode,

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

        // Slang Validation Config
        SLANG_VALIDATION_AUTO_APPROVAL_ENABLED: backendConfig.slang_validation.auto_approval_enabled.toString(),
        SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD: backendConfig.slang_validation.auto_approval_threshold.toString(),
        SLANG_VALIDATION_WEB_SEARCH_ENABLED: backendConfig.slang_validation.web_search_enabled.toString(),
        SLANG_VALIDATION_MAX_SEARCH_RESULTS: backendConfig.slang_validation.max_search_results.toString(),

        // Slang Submission Config (SNS Topic ARNs)
        SLANG_SUBMISSIONS_TOPIC_ARN: this.slangSubmissionsTopic.topicArn,
        SLANG_VALIDATION_REQUEST_TOPIC_ARN: this.slangValidationRequestTopic.topicArn,

        // Quiz Configuration
        QUIZ_FREE_DAILY_LIMIT: "3",
        QUIZ_QUESTIONS_PER_QUIZ: "10",
        QUIZ_TIME_LIMIT_SECONDS: "60",

        // Apple Config (for App Store Server API)
        APPLE_KEY_ID: config.apple.in_app_purchase_key_id,
        APPLE_ISSUER_ID: config.apple.issuer_id,
        APPLE_BUNDLE_ID: config.apple.bundle_id,
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
          this.slangTermsTable.tableArn,
          `${this.usersTable.tableArn}/index/*`,
          `${this.translationsTable.tableArn}/index/*`,
          `${this.trendingTable.tableArn}/index/*`,
          `${this.slangTermsTable.tableArn}/index/*`,
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
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:ListBucket',
        ],
        resources: [
          this.lexiconBucket.bucketArn,
        ],
      }),
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:GetObject',
          's3:GetObjectVersion',
        ],
        resources: [
          `${this.lexiconBucket.bucketArn}/*`,
        ],
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

    // Create monitoring (after Lambda functions are created)
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
    usersTableConfig: { name: string; read_capacity: number; write_capacity: number },
    translationsTableConfig: { name: string; read_capacity: number; write_capacity: number },
    trendingTableConfig: { name: string; read_capacity: number; write_capacity: number },
    slangTermsTableConfig: { name: string; read_capacity: number; write_capacity: number }
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

    // Slang Terms table (unified for submissions, lexicon, quiz)
    // Note: Using 'SlangSubmissionsTable' construct ID to match existing CloudFormation resource
    // The table name remains lingible-slang-submissions-dev but conceptually holds slang_terms
    this.slangTermsTable = new dynamodb.Table(this, 'SlangSubmissionsTable', {
      tableName: slangTermsTableConfig.name,
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

    // GSI1 - Query by status (existing functionality)
    this.slangTermsTable.addGlobalSecondaryIndex({
      indexName: 'GSI1',
      partitionKey: {
        name: 'GSI1PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GSI1SK',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // NOTE: For prod deployment with existing table, deploy GSIs incrementally:
    // 1. ✅ GSIs 2-5 are commented out below
    // 2. Deploy with just GSI1
    // 3. Uncomment GSI2, deploy
    // 4. Uncomment GSI3, deploy
    // 5. Uncomment GSI4, deploy
    // 6. Uncomment GSI5, deploy
    // DynamoDB only allows one GSI creation/deletion per update

    // GSI2 - Quiz queries by difficulty
    this.slangTermsTable.addGlobalSecondaryIndex({
      indexName: 'GSI2',
      partitionKey: {
        name: 'GSI2PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GSI2SK',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI3 - Category queries
    this.slangTermsTable.addGlobalSecondaryIndex({
      indexName: 'GSI3',
      partitionKey: {
        name: 'GSI3PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GSI3SK',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI4 - Source queries
    this.slangTermsTable.addGlobalSecondaryIndex({
      indexName: 'GSI4',
      partitionKey: {
        name: 'GSI4PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GSI4SK',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI5 - Quiz history queries (for user quiz history)
    this.slangTermsTable.addGlobalSecondaryIndex({
      indexName: 'GSI5',
      partitionKey: {
        name: 'GSI5PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GSI5SK',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

  }

  private createLexiconBucket(bucketName: string): void {
    // Create S3 bucket for lexicon storage
    this.lexiconBucket = new s3.Bucket(this, 'LexiconBucket', {
      bucketName: bucketName,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      autoDeleteObjects: true, // Automatically delete objects when bucket is destroyed
      versioned: false, // Lexicon files don't need versioning
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
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

  private createCoreLayer(environment: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, 'CoreLayer', {
      layerVersionName: `lingible-core-layer-${environment}`,
      code: lambda.Code.fromAsset('./lambda-core-layer', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          platform: 'linux/arm64',
          command: [
            'bash', '-c',
            'rm -rf /asset-output/python && pip install --platform manylinux2014_aarch64 --implementation cp --python-version 3.13 --only-binary=:all: --upgrade --target /asset-output/python -r requirements.txt'
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Core dependencies for Lingible Lambda functions',
    });
  }

  private createReceiptValidationLayer(environment: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, 'ReceiptValidationLayer', {
      layerVersionName: `lingible-receipt-validation-layer-${environment}`,
      code: lambda.Code.fromAsset('./lambda-receipt-validation-layer', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          platform: 'linux/arm64',
          command: [
            'bash', '-c',
            'rm -rf /asset-output/python && pip install --platform manylinux2014_aarch64 --implementation cp --python-version 3.13 --only-binary=:all: --upgrade --target /asset-output/python -r requirements.txt'
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Receipt validation dependencies for Lingible Lambda functions',
    });
  }

  private createSlangValidationLayer(environment: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, 'SlangValidationLayer', {
      layerVersionName: `lingible-slang-validation-layer-${environment}`,
      code: lambda.Code.fromAsset('./lambda-slang-validation-layer', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          platform: 'linux/arm64',
          command: [
            'bash', '-c',
            'rm -rf /asset-output/python && pip install --platform manylinux2014_aarch64 --implementation cp --python-version 3.13 --only-binary=:all: --upgrade --target /asset-output/python -r requirements.txt'
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Slang validation dependencies (requests) for Lingible Lambda functions',
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

  private createLambdaFunctions(
    environment: string,
    lambdaConfig: any,
    lambdaPolicyStatements: iam.PolicyStatement[],
    baseEnvironmentVariables: { [key: string]: string }
  ): void {
    // API Handlers
    const config = this.configLoader.getMergedConfig(environment);
    const backendConfig = this.configLoader.loadBackendConfig(environment);

    this.translateLambda = new lambda.Function(this, 'TranslateLambda', {
      functionName: `lingible-translate-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.translate_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-translate',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 512,
      timeout: Duration.seconds(30),
    });

    // Add provisioned concurrency for production translate function
    // Note: Temporarily disabled due to account concurrent execution limits
    // TODO: Re-enable when account limits are increased
    if (false && environment === 'prod') {
      // Create a new version of the function (required for provisioned concurrency)
      const translateVersion = this.translateLambda.currentVersion;

      // Create an alias for the function with provisioned concurrency
      this.translateAlias = new lambda.CfnAlias(this, 'TranslateAliasWithProvisionedConcurrency', {
        functionName: this.translateLambda.functionName,
        functionVersion: translateVersion.version,
        name: 'live',
        provisionedConcurrencyConfig: {
          provisionedConcurrentExecutions: 1,
        },
      });
    }
    lambdaPolicyStatements.forEach(statement => this.translateLambda.addToRolePolicy(statement));

    // Add Bedrock permissions for translation Lambda
    this.translateLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
      ],
      resources: [
        `arn:aws:bedrock:${config.bedrock.region}::foundation-model/${backendConfig.llm.model}`,
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
      layers: [this.coreLayer, this.sharedLayer],

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
      layers: [this.coreLayer, this.sharedLayer],

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
      layers: [this.receiptValidationLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 384,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.userUpgradeLambda.addToRolePolicy(statement));

    // Add secrets permissions for StoreKit 2 validation
    this.userUpgradeLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-iap-private-key-${environment}*`,
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
      layers: [this.receiptValidationLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 384,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.userAccountDeletionLambda.addToRolePolicy(statement));

    // Add secrets permissions for StoreKit 2 validation
    this.userAccountDeletionLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-iap-private-key-${environment}*`,
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
      layers: [this.coreLayer, this.sharedLayer],

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
      layers: [this.coreLayer, this.sharedLayer],

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
      layers: [this.coreLayer, this.sharedLayer],

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
      layers: [this.coreLayer, this.sharedLayer],

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
      layers: [this.coreLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.trendingLambda.addToRolePolicy(statement));

    this.submitSlangLambda = new lambda.Function(this, 'SubmitSlangLambda', {
      functionName: `lingible-submit-slang-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.submit_slang_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-submit-slang',
        ...baseEnvironmentVariables,
        SLANG_SUBMISSIONS_TOPIC_ARN: this.slangSubmissionsTopic.topicArn,
        SLANG_VALIDATION_REQUEST_TOPIC_ARN: this.slangValidationRequestTopic.topicArn,
      },
      layers: [this.coreLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.submitSlangLambda.addToRolePolicy(statement));

    // Grant SNS publish permissions for slang submissions
    this.slangSubmissionsTopic.grantPublish(this.submitSlangLambda);

    // Grant SNS publish permissions for validation requests
    this.slangValidationRequestTopic.grantPublish(this.submitSlangLambda);


    // Slang Upvote Handler
    this.slangUpvoteLambda = new lambda.Function(this, 'SlangUpvoteLambda', {
      functionName: `lingible-slang-upvote-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.slang_upvote_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-slang-upvote',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(15),
    });
    lambdaPolicyStatements.forEach(statement => this.slangUpvoteLambda.addToRolePolicy(statement));

    // Slang Pending Submissions Handler
    this.slangPendingLambda = new lambda.Function(this, 'SlangPendingLambda', {
      functionName: `lingible-slang-pending-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.slang_pending_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-slang-pending',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(15),
    });
    lambdaPolicyStatements.forEach(statement => this.slangPendingLambda.addToRolePolicy(statement));

    // Slang Admin Approve Handler
    this.slangAdminApproveLambda = new lambda.Function(this, 'SlangAdminApproveLambda', {
      functionName: `lingible-slang-admin-approve-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.slang_admin_approve_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-slang-admin-approve',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(15),
    });
    lambdaPolicyStatements.forEach(statement => this.slangAdminApproveLambda.addToRolePolicy(statement));

    // Slang Admin Reject Handler
    this.slangAdminRejectLambda = new lambda.Function(this, 'SlangAdminRejectLambda', {
      functionName: `lingible-slang-admin-reject-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.slang_admin_reject_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-slang-admin-reject',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(15),
    });
    lambdaPolicyStatements.forEach(statement => this.slangAdminRejectLambda.addToRolePolicy(statement));

    // Slang Validation Processor
    this.slangValidationProcessorLambda = new lambda.Function(this, 'SlangValidationProcessorLambda', {
      functionName: `lingible-slang-validation-processor-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.slang_validation_processor.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-slang-validation-processor',
        ...baseEnvironmentVariables,
        SLANG_SUBMISSIONS_TOPIC_ARN: this.slangSubmissionsTopic.topicArn,
      },
      layers: [this.slangValidationLayer, this.sharedLayer],
      ...lambdaConfig,
      memorySize: 512,
      timeout: Duration.seconds(60), // Longer timeout for web search + LLM
    });
    lambdaPolicyStatements.forEach(statement => this.slangValidationProcessorLambda.addToRolePolicy(statement));

    // Add secrets permissions for Tavily API key
    this.slangValidationProcessorLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-tavily-api-key-${environment}*`,
      ],
    }));

    // Add SNS subscription for validation requests
    this.slangValidationRequestTopic.addSubscription(
      new snsSubscriptions.LambdaSubscription(this.slangValidationProcessorLambda)
    );

    // Export Lexicon Lambda
    this.exportLexiconLambda = new lambda.Function(this, 'ExportLexiconLambda', {
      functionName: `lingible-export-lexicon-${environment}`,
      handler: 'handler.lambda_handler',
      code: this.createHandlerPackage('src.handlers.export_lexicon_handler.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-export-lexicon',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
      timeout: Duration.minutes(5), // Longer timeout for large exports
    });
    lambdaPolicyStatements.forEach(statement => this.exportLexiconLambda.addToRolePolicy(statement));

    // Grant DynamoDB read and S3 write for export Lambda
    this.slangTermsTable.grantReadData(this.exportLexiconLambda);
    this.lexiconBucket.grantWrite(this.exportLexiconLambda);

    // Subscribe export lexicon to slang submissions topic (only approval events)
    this.slangSubmissionsTopic.addSubscription(
      new snsSubscriptions.LambdaSubscription(this.exportLexiconLambda, {
        filterPolicy: {
          notification_type: sns.SubscriptionFilter.stringFilter({
            allowlist: ['auto_approval', 'manual_approval']
          })
        }
      })
    );

    // Quiz Challenge Lambda
    this.quizChallengeLambda = new lambda.Function(this, 'QuizChallengeLambda', {
      functionName: `lingible-quiz-challenge-${environment}`,
      handler: 'handler.lambda_handler',
      code: this.createHandlerPackage('src.handlers.quiz_challenge_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-quiz-challenge',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.quizChallengeLambda.addToRolePolicy(statement));

    // Quiz Submit Lambda
    this.quizSubmitLambda = new lambda.Function(this, 'QuizSubmitLambda', {
      functionName: `lingible-quiz-submit-${environment}`,
      handler: 'handler.lambda_handler',
      code: this.createHandlerPackage('src.handlers.quiz_submit_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-quiz-submit',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.quizSubmitLambda.addToRolePolicy(statement));

    // Quiz History Lambda
    this.quizHistoryLambda = new lambda.Function(this, 'QuizHistoryLambda', {
      functionName: `lingible-quiz-history-${environment}`,
      handler: 'handler.lambda_handler',
      code: this.createHandlerPackage('src.handlers.quiz_history_api.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-quiz-history',
        ...baseEnvironmentVariables,
      },
      layers: [this.coreLayer, this.sharedLayer],
      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.quizHistoryLambda.addToRolePolicy(statement));

    // Webhook Handlers
    this.appleWebhookLambda = new lambda.Function(this, 'AppleWebhookLambda', {
      functionName: `lingible-apple-webhook-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.apple_webhook.handler'),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'lingible-apple-webhook',
        ...baseEnvironmentVariables,
      },
      layers: [this.receiptValidationLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 384,
      timeout: Duration.seconds(30),
    });
    lambdaPolicyStatements.forEach(statement => this.appleWebhookLambda.addToRolePolicy(statement));

    // Add secrets permissions for StoreKit 2 validation
    this.appleWebhookLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-iap-private-key-${environment}*`,
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
      layers: [this.coreLayer, this.sharedLayer],

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
      layers: [this.receiptValidationLayer, this.sharedLayer],

      ...lambdaConfig,
      memorySize: 256,
      timeout: Duration.seconds(60),
    });
    lambdaPolicyStatements.forEach(statement => this.userDataCleanupLambda.addToRolePolicy(statement));

    // Add secrets permissions for StoreKit 2 validation
    this.userDataCleanupLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:lingible-apple-iap-private-key-${environment}*`,
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
      layers: [this.coreLayer, this.sharedLayer],

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

    // Create native Cognito authorizer
    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'NativeCognitoAuthorizer', {
      cognitoUserPools: [this.userPool],
      authorizerName: 'NativeCognitoAuthorizer',
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
    this.createApiResources(cognitoAuthorizer, errorModel, successModel);

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
    cognitoAuthorizer: apigateway.CognitoUserPoolsAuthorizer,
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
      // Use alias for production (with provisioned concurrency) or function for dev
      const translateIntegration = this.translateAlias
        ? new apigateway.LambdaIntegration(
            lambda.Function.fromFunctionArn(this, 'TranslateAliasFunction',
              `${this.translateLambda.functionArn}:${this.translateAlias.name}`)
          )
        : new apigateway.LambdaIntegration(this.translateLambda);

    translate.addMethod('POST', translateIntegration, {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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

    // Slang submission endpoint
    const slang = this.api.root.addResource('slang');
    const submit = slang.addResource('submit');
    submit.addMethod('POST', new apigateway.LambdaIntegration(this.submitSlangLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
          statusCode: '403',
          responseModels: {
            'application/json': errorModel,
          },
        },
        {
          statusCode: '429',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // Slang pending submissions endpoint
    const pending = slang.addResource('pending');
    pending.addMethod('GET', new apigateway.LambdaIntegration(this.slangPendingLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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

    // Slang upvote endpoint
    const upvote = slang.addResource('upvote');
    const upvoteSubmission = upvote.addResource('{submission_id}');
    upvoteSubmission.addMethod('POST', new apigateway.LambdaIntegration(this.slangUpvoteLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
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
          statusCode: '404',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // Slang admin endpoints
    const admin = slang.addResource('admin');
    const approve = admin.addResource('approve');
    const approveSubmission = approve.addResource('{submission_id}');
    approveSubmission.addMethod('POST', new apigateway.LambdaIntegration(this.slangAdminApproveLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      // TODO: Add admin tier check in authorizer or use request validator
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
        {
          statusCode: '403',
          responseModels: {
            'application/json': errorModel,
          },
        },
        {
          statusCode: '404',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    const reject = admin.addResource('reject');
    const rejectSubmission = reject.addResource('{submission_id}');
    rejectSubmission.addMethod('POST', new apigateway.LambdaIntegration(this.slangAdminRejectLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      // TODO: Add admin tier check in authorizer or use request validator
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
        {
          statusCode: '403',
          responseModels: {
            'application/json': errorModel,
          },
        },
        {
          statusCode: '404',
          responseModels: {
            'application/json': errorModel,
          },
        },
      ],
    });

    // Quiz endpoints
    const quiz = this.api.root.addResource('quiz');

    // Quiz challenge endpoint
    const challenge = quiz.addResource('challenge');
    challenge.addMethod('GET', new apigateway.LambdaIntegration(this.quizChallengeLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': apigateway.Model.EMPTY_MODEL,
          },
        },
      ],
    });

    // Quiz submit endpoint
    const submitQuiz = quiz.addResource('submit');
    submitQuiz.addMethod('POST', new apigateway.LambdaIntegration(this.quizSubmitLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': apigateway.Model.EMPTY_MODEL,
          },
        },
      ],
    });

    // Quiz history endpoint
    const history = quiz.addResource('history');
    history.addMethod('GET', new apigateway.LambdaIntegration(this.quizHistoryLambda), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': apigateway.Model.EMPTY_MODEL,
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

  private createSnsTopics(environment: string): void {
    // Create SNS topic for alerts
    this.alertTopic = new sns.Topic(this, 'AlertTopic', {
      topicName: `lingible-alerts-${environment}`,
      displayName: `Lingible ${environment} Alerts`,
    });

    // Create SNS topic for slang submissions
    this.slangSubmissionsTopic = new sns.Topic(this, 'SlangSubmissionsTopic', {
      topicName: `lingible-slang-submissions-${environment}`,
      displayName: `Lingible ${environment} Slang Submissions`,
    });

    // Create SNS topic for slang validation requests
    this.slangValidationRequestTopic = new sns.Topic(this, 'SlangValidationRequestTopic', {
      topicName: `lingible-slang-validation-requests-${environment}`,
      displayName: `Lingible ${environment} Slang Validation Requests`,
    });
  }

  private createMonitoring(environment: string): void {

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

    // Cost monitoring alarm for Bedrock usage
    new cloudwatch.Alarm(this, 'HighBedrockCosts', {
      metric: new cloudwatch.Metric({
        namespace: 'AWS/Bedrock',
        metricName: 'InputTokens',
        statistic: 'Sum',
        period: Duration.days(1),
      }),
      threshold: 1000000, // Alert if > 1M tokens per day (~$1-2 at Haiku pricing)
      evaluationPeriods: 1,
      alarmDescription: 'High Bedrock token usage - check slang validation costs',
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(new actions.SnsAction(this.alertTopic));

    // Slang submission rate alarm (unusual activity detection)
    new cloudwatch.Alarm(this, 'HighSlangSubmissions', {
      metric: this.submitSlangLambda.metricInvocations({
        statistic: 'Sum',
        period: Duration.hours(1),
      }),
      threshold: 100, // Alert if > 100 submissions per hour
      evaluationPeriods: 1,
      alarmDescription: 'Unusually high slang submission rate - possible abuse',
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
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
          model: backendConfig.llm.model,
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
          model: backendConfig.llm.model,
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
