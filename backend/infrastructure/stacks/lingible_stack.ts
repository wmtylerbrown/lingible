import * as cdk from 'aws-cdk-lib';
import * as route53 from 'aws-cdk-lib/aws-route53';
import { Construct } from 'constructs';
import { BackendStack } from '../constructs/backend_stack';

export class LingibleStack extends cdk.Stack {
  public readonly backendStack: BackendStack;

  constructor(
    scope: Construct,
    id: string,
    props: cdk.StackProps & {
      environment: string;
      appleClientId?: string;
      appleTeamId?: string;
      appleKeyId?: string;
    }
  ) {
    super(scope, id, props);

    const environment = props.environment;

    // Import the hosted zone from the separately deployed HostedZonesStack
    const hostedZoneId = cdk.Fn.importValue(`Lingible-${environment}-HostedZoneId`);
    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, 'ImportedHostedZone', {
      hostedZoneId: hostedZoneId,
      zoneName: `${environment}.lingible.com`,
    });

    // Backend Stack (combines database, cognito/lambda, API gateway, and monitoring)
    this.backendStack = new BackendStack(this, 'Backend', {
      environment: environment,
      hostedZone: hostedZone,
      appleClientId: props.appleClientId,
      appleTeamId: props.appleTeamId,
      appleKeyId: props.appleKeyId,
    });
  }
}
