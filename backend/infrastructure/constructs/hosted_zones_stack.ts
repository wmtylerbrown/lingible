import * as cdk from 'aws-cdk-lib';
import * as route53 from 'aws-cdk-lib/aws-route53';
import { Construct } from 'constructs';

// Construct version for use within other stacks
export class HostedZonesConstruct extends Construct {
  public readonly hostedZone: route53.HostedZone;

  constructor(scope: Construct, id: string, props: { environment: string }) {
    super(scope, id);

    const environment = props.environment;

    // Create hosted zone for the current environment only
    // Note: This stack should be deployed first, before main application stacks

    // Environment-specific hosted zone
    const zoneName = `${environment}.lingible.com`;
    this.hostedZone = new route53.HostedZone(this, `${environment.charAt(0).toUpperCase() + environment.slice(1)}HostedZone`, {
      zoneName: zoneName,
    });

    // Outputs for other stacks to reference
    new cdk.CfnOutput(this, 'HostedZoneId', {
      value: this.hostedZone.hostedZoneId,
      description: `${environment.charAt(0).toUpperCase() + environment.slice(1)} hosted zone ID`,
      exportName: `Lingible-${environment}-HostedZoneId`,
    });

    new cdk.CfnOutput(this, 'HostedZoneNameServers', {
      value: cdk.Fn.join(',', this.hostedZone.hostedZoneNameServers || []),
      description: `${environment.charAt(0).toUpperCase() + environment.slice(1)} hosted zone name servers (for Squarespace DNS)`,
      exportName: `Lingible-${environment}-NameServers`,
    });

    // Add helpful deployment instructions
    new cdk.CfnOutput(this, 'DeploymentInstructions', {
      value: `After deployment, add NS record in Squarespace DNS for ${zoneName} pointing to the name servers above. This creates only the hosted zone - certificates will be created separately when needed.`,
      description: 'Next steps for DNS configuration',
    });
  }
}

// Stack version for standalone deployment
export class HostedZonesStack extends cdk.Stack {
  public readonly hostedZonesConstruct: HostedZonesConstruct;

  constructor(scope: Construct, id: string, props: cdk.StackProps & { environment: string }) {
    super(scope, id, props);

    const environment = props.environment;

    // Create the hosted zones construct
    this.hostedZonesConstruct = new HostedZonesConstruct(this, 'HostedZones', {
      environment: environment,
    });

    // Add tags to all resources
    cdk.Tags.of(this).add('Application', 'Lingible');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Component', 'HostedZones');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');
  }
}
