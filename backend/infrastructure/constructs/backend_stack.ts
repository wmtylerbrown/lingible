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
import * as ssm from 'aws-cdk-lib/aws-ssm';

import { Duration, RemovalPolicy, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as fs from 'fs';
import * as path from 'path';
import { ConfigLoader } from '../utils/config-loader';

export class BackendStack extends Construct {
  // Database resources
  public usersTable!: dynamodb.Table;
  public translationsTable!: dynamodb.Table;

  // Cognito resources
  public userPool!: cognito.UserPool;
  public userPoolClient!: cognito.UserPoolClient;

  // Lambda layers
  public sharedLayer!: lambda.LayerVersion;
  public dependenciesLayer!: lambda.LayerVersion;

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

  // Configuration loader
  private configLoader!: ConfigLoader;
  private environment!: string;
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

    // Create Lambda layers
    this.dependenciesLayer = this.createDependenciesLayer(environment);
    this.sharedLayer = this.createSharedLayer(environment);

    // Create DynamoDB tables
    this.createDatabaseTables(environment, config.users_table, config.translations_table);
    const lambdaConfig = {
      runtime: lambda.Runtime.PYTHON_3_13,
      timeout: Duration.seconds(30),
      memorySize: 512,
      logRetention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY, // For development
      ...this.configLoader.getLambdaConfig(environment),
    };

    // Create SSM parameters for configuration
    this.createSsmParameters(environment, config);

    // Common environment variables function
    const getCommonEnv = () => {
      const baseEnv: { [key: string]: string } = {
        POWERTOOLS_SERVICE_NAME: 'lingible-api',
        LOG_LEVEL: 'INFO',
        POWERTOOLS_LOGGER_LOG_EVENT: 'true',
        USERS_TABLE: this.usersTable.tableName,
        TRANSLATIONS_TABLE: this.translationsTable.tableName,
        ENVIRONMENT: environment,
        APP_NAME: 'lingible',
      };
      return baseEnv;
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
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'ssm:GetParameter',
          'ssm:GetParameters',
          'ssm:GetParametersByPath',
        ],
        resources: [
          `arn:aws:ssm:*:*:parameter/lingible/${environment}/*`,
        ],
      }),
    ];

    // Create Cognito User Pool
    this.createCognitoUserPool(environment, appleClientId, appleTeamId, appleKeyId);

    // Create Lambda functions
    this.createLambdaFunctions(environment, getCommonEnv, lambdaConfig, lambdaPolicyStatements);

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

  private createDatabaseTables(
    environment: string,
    usersTableConfig: { name: string; read_capacity: number; write_capacity: number },
    translationsTableConfig: { name: string; read_capacity: number; write_capacity: number }
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


  }

  private createSsmParameters(environment: string, config: any): void {
    const appName = 'lingible';
    const parameterPrefix = `/${appName}/${environment}`;

    // App-wide configuration parameters
    new ssm.StringParameter(this, 'AppConfigParameter', {
      parameterName: `${parameterPrefix}/app`,
      stringValue: JSON.stringify(config.app),
      description: 'App configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'TranslationConfigParameter', {
      parameterName: `${parameterPrefix}/translation`,
      stringValue: JSON.stringify(config.translation),
      description: 'Translation configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'LimitsConfigParameter', {
      parameterName: `${parameterPrefix}/limits`,
      stringValue: JSON.stringify(config.limits),
      description: 'Usage limits configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'SecurityConfigParameter', {
      parameterName: `${parameterPrefix}/security`,
      stringValue: JSON.stringify(config.security),
      description: 'Security configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'ApiConfigParameter', {
      parameterName: `${parameterPrefix}/api`,
      stringValue: JSON.stringify(config.api),
      description: 'API configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'StoresConfigParameter', {
      parameterName: `${parameterPrefix}/stores`,
      stringValue: JSON.stringify(config.stores),
      description: 'Store configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    // Environment-specific configuration parameters
    new ssm.StringParameter(this, 'AwsConfigParameter', {
      parameterName: `${parameterPrefix}/aws`,
      stringValue: JSON.stringify(config.aws),
      description: 'AWS configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'BedrockConfigParameter', {
      parameterName: `${parameterPrefix}/bedrock`,
      stringValue: JSON.stringify(config.bedrock),
      description: 'Bedrock configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'CognitoConfigParameter', {
      parameterName: `${parameterPrefix}/cognito`,
      stringValue: JSON.stringify(config.cognito),
      description: 'Cognito configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'UsersTableConfigParameter', {
      parameterName: `${parameterPrefix}/users_table`,
      stringValue: JSON.stringify(config.users_table),
      description: 'Users table configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'TranslationsTableConfigParameter', {
      parameterName: `${parameterPrefix}/translations_table`,
      stringValue: JSON.stringify(config.translations_table),
      description: 'Translations table configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'AppleConfigParameter', {
      parameterName: `${parameterPrefix}/apple`,
      stringValue: JSON.stringify(config.apple),
      description: 'Apple configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'GoogleConfigParameter', {
      parameterName: `${parameterPrefix}/google`,
      stringValue: JSON.stringify(config.google),
      description: 'Google configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'ObservabilityConfigParameter', {
      parameterName: `${parameterPrefix}/observability`,
      stringValue: JSON.stringify(config.observability),
      description: 'Observability configuration for Lingible',
      tier: ssm.ParameterTier.STANDARD,
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

  private createDependenciesLayer(environment: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, 'DependenciesLayer', {
      layerVersionName: `lingible-dependencies-layer-${environment}`,
      code: lambda.Code.fromAsset('../lambda', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          command: [
            'bash', '-c',
            'rm -rf /asset-output/python && pip install --platform manylinux2014_x86_64 --implementation cp --python-version 3.13 --only-binary=:all: --upgrade --target /asset-output/python -r requirements.txt'
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
      code: lambda.Code.fromAsset('../lambda/src', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          command: [
            'bash', '-c',
            'mkdir -p /asset-output/python && cp -r services repositories models utils /asset-output/python/ && find /asset-output/python -name "*.pyc" -delete && find /asset-output/python -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true'
          ]
        },
        exclude: [
          '**/__pycache__/**',
          '**/*.pyc',
          '**/*.pyo',
          '**/*.pyd',
          '**/.pytest_cache/**',
          '**/.coverage',
          '**/.mypy_cache/**',
          '**/tests/**',
          '**/handlers/**'
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
    getCommonEnv: any,
    lambdaConfig: any,
    lambdaPolicyStatements: iam.PolicyStatement[]
  ): void {
    // API Handlers
    this.authorizerLambda = new lambda.Function(this, 'AuthorizerLambda', {
      functionName: `lingible-authorizer-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.authorizer.authorizer'),
      environment: {
        ...getCommonEnv(),
        USER_POOL_ID: this.userPool.userPoolId,
        USER_POOL_CLIENT_ID: this.userPoolClient.userPoolClientId,
        API_GATEWAY_ARN: `arn:aws:execute-api:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:*`,
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.authorizerLambda.addToRolePolicy(statement));

    this.translateLambda = new lambda.Function(this, 'TranslateLambda', {
      functionName: `lingible-translate-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.translate_api.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.translateLambda.addToRolePolicy(statement));

    // Add Bedrock permissions for translation Lambda
    this.translateLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
      ],
      resources: [
        (() => {
          const bedrock = this.configLoader.getBedrockConfig(this.environment);
          return `arn:aws:bedrock:${bedrock.region}::foundation-model/${bedrock.model}`;
        })(),
      ],
    }));

    this.userProfileLambda = new lambda.Function(this, 'UserProfileLambda', {
      functionName: `lingible-user-profile-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_profile_api.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.userProfileLambda.addToRolePolicy(statement));

    this.userUsageLambda = new lambda.Function(this, 'UserUsageLambda', {
      functionName: `lingible-user-usage-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_usage_api.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.userUsageLambda.addToRolePolicy(statement));

    this.userUpgradeLambda = new lambda.Function(this, 'UserUpgradeLambda', {
      functionName: `lingible-user-upgrade-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_upgrade_api.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.userUpgradeLambda.addToRolePolicy(statement));

    this.translationHistoryLambda = new lambda.Function(this, 'TranslationHistoryLambda', {
      functionName: `lingible-translation-history-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.get_translation_history.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.translationHistoryLambda.addToRolePolicy(statement));

    this.deleteTranslationLambda = new lambda.Function(this, 'DeleteTranslationLambda', {
      functionName: `lingible-delete-translation-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.delete_translation.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.deleteTranslationLambda.addToRolePolicy(statement));

    this.deleteAllTranslationsLambda = new lambda.Function(this, 'DeleteAllTranslationsLambda', {
      functionName: `lingible-delete-all-translations-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.delete_translations.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.deleteAllTranslationsLambda.addToRolePolicy(statement));

    this.healthLambda = new lambda.Function(this, 'HealthLambda', {
      functionName: `lingible-health-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.health_api.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.healthLambda.addToRolePolicy(statement));

    // Webhook Handlers
    this.appleWebhookLambda = new lambda.Function(this, 'AppleWebhookLambda', {
      functionName: `lingible-apple-webhook-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.apple_webhook.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.appleWebhookLambda.addToRolePolicy(statement));

    // Cognito Triggers
    this.postConfirmationLambda = new lambda.Function(this, 'PostConfirmationLambda', {
      functionName: `lingible-post-confirmation-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.cognito_post_confirmation.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

      ...lambdaConfig,
    });
    lambdaPolicyStatements.forEach(statement => this.postConfirmationLambda.addToRolePolicy(statement));



    // Background Processing
    this.userDataCleanupLambda = new lambda.Function(this, 'UserDataCleanupLambda', {
      functionName: `lingible-user-data-cleanup-${environment}`,
      handler: 'handler.handler',
      code: this.createHandlerPackage('src.handlers.user_data_cleanup.handler'),
      environment: {
        ...getCommonEnv(),
      },
      layers: [this.dependenciesLayer, this.sharedLayer],

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
