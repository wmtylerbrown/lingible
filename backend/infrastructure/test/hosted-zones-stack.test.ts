import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { HostedZonesConstruct } from '../constructs/hosted_zones_stack';

describe('HostedZonesConstruct', () => {
  let stack: cdk.Stack;
  let hostedZones: HostedZonesConstruct;
  let template: Template;

  beforeEach(() => {
    const app = new cdk.App();
    stack = new cdk.Stack(app, 'TestStack', {
      env: {
        account: '123456789012',
        region: 'us-east-1',
      },
    });
    hostedZones = new HostedZonesConstruct(stack, 'HostedZones', {
      environment: 'dev',
    });
    template = Template.fromStack(stack);
  });

  test('creates a hosted zone', () => {
    template.hasResourceProperties('AWS::Route53::HostedZone', {
      Name: 'dev.lingible.com.',
    });
  });

  test('creates hosted zone outputs', () => {
    // Check that outputs exist with the correct descriptions
    const outputs = template.findOutputs('*');
    const hostedZoneIdOutput = Object.values(outputs).find(output =>
      output.Description === 'Dev hosted zone ID'
    );
    const nameServersOutput = Object.values(outputs).find(output =>
      output.Description === 'Dev hosted zone name servers (for Squarespace DNS)'
    );

    expect(hostedZoneIdOutput).toBeDefined();
    expect(nameServersOutput).toBeDefined();
  });

  test('exports hosted zone ID', () => {
    // Check that an output exists with the correct export name
    const outputs = template.findOutputs('*');
    const hostedZoneIdOutput = Object.values(outputs).find(output =>
      output.Export?.Name === 'Lingible-dev-HostedZoneId'
    );
    expect(hostedZoneIdOutput).toBeDefined();
  });

  test('exports name servers', () => {
    // Check that an output exists with the correct export name
    const outputs = template.findOutputs('*');
    const nameServersOutput = Object.values(outputs).find(output =>
      output.Export?.Name === 'Lingible-dev-NameServers'
    );
    expect(nameServersOutput).toBeDefined();
  });
});
