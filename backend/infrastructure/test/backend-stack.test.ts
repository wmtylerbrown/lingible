import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as route53 from 'aws-cdk-lib/aws-route53';
import { BackendStack } from '../constructs/backend_stack';

describe('BackendStack', () => {
  let app: cdk.App;
  let stack: BackendStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();

    // Create a mock hosted zone for testing
    const mockStack = new cdk.Stack(app, 'MockStack', {
      env: {
        account: '123456789012',
        region: 'us-east-1',
      },
    });

    const mockHostedZone = new route53.HostedZone(mockStack, 'MockHostedZone', {
      zoneName: 'dev.lingible.com',
    });

    // Create the backend stack
    stack = new BackendStack(mockStack, 'TestBackendStack', {
      environment: 'dev',
      hostedZone: mockHostedZone,
    });

    template = Template.fromStack(mockStack);
  });

  test('creates DynamoDB tables', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'lingible-users-dev',
    });

    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'lingible-translations-dev',
    });
  });

  test('creates Cognito User Pool', () => {
    template.hasResourceProperties('AWS::Cognito::UserPool', {
      UserPoolName: 'lingible-user-pool-dev',
    });
  });

  test('creates Cognito User Pool Client', () => {
    template.hasResourceProperties('AWS::Cognito::UserPoolClient', {
      ClientName: 'lingible-client-dev',
    });
  });

  test('creates Lambda functions', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'lingible-authorizer-dev',
    });

    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'lingible-translate-dev',
    });

    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'lingible-health-dev',
    });
  });

  test('creates API Gateway', () => {
    template.hasResourceProperties('AWS::ApiGateway::RestApi', {
      Name: 'lingible-api-dev',
    });
  });

  test('creates SSL certificate', () => {
    template.hasResourceProperties('AWS::CertificateManager::Certificate', {
      DomainName: 'api.dev.lingible.com',
    });
  });

  test('creates CloudWatch Dashboard', () => {
    template.hasResourceProperties('AWS::CloudWatch::Dashboard', {
      DashboardName: 'Lingible-dev',
    });
  });

  test('creates SNS Topic', () => {
    template.hasResourceProperties('AWS::SNS::Topic', {
      TopicName: 'lingible-alerts-dev',
    });
  });

  test('creates outputs', () => {
    template.hasOutput('UserPoolId', {
      Description: 'Cognito User Pool ID',
    });

    template.hasOutput('ApiUrl', {
      Description: 'API Gateway URL',
    });

    template.hasOutput('UsersTableName', {
      Description: 'Users DynamoDB table name',
    });
  });
});
