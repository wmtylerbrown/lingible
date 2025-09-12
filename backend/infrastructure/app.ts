#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ConfigLoader } from './utils/config-loader';
import * as fs from 'fs';
import * as path from 'path';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const environment = app.node.tryGetContext('environment') || 'dev';

// Check if we should deploy the full stack or just hosted zones
const deployBackendContext = app.node.tryGetContext('deploy-backend');
const deployBackend = deployBackendContext !== 'false' && deployBackendContext !== false; // Default to true

// Load application configuration from shared config (only for full stack deployment)
let appleCredentials: { clientId: string; teamId: string; keyId: string } | undefined;
if (deployBackend) {
  try {
    const configLoader = new ConfigLoader(path.resolve(__dirname, '../..'));
    const infrastructureConfig = configLoader.loadInfrastructureConfig(environment);
    appleCredentials = {
      clientId: infrastructureConfig.apple.client_id,
      teamId: infrastructureConfig.apple.team_id,
      keyId: infrastructureConfig.apple.key_id
    };
  } catch (error) {
    console.warn('⚠️  Failed to load Apple credentials from shared config. Using default values.');
    appleCredentials = { clientId: 'TO_BE_SET', teamId: 'TO_BE_SET', keyId: 'TO_BE_SET' };
  }
}

if (deployBackend) {
  // Full stack deployment (hosted zones + backend)
  if (!appleCredentials) {
    throw new Error('Apple credentials are required for full stack deployment');
  }
  const { LingibleStack } = require('./stacks/lingible_stack');
  new LingibleStack(app, `Lingible-${environment.charAt(0).toUpperCase() + environment.slice(1)}`, {
    description: `Lingible - ${environment.charAt(0).toUpperCase() + environment.slice(1)} Environment`,
    environment: environment,
    appleClientId: appleCredentials.clientId,
    appleTeamId: appleCredentials.teamId,
    appleKeyId: appleCredentials.keyId,
    env: {
      account: app.node.tryGetContext('account') || process.env.CDK_DEFAULT_ACCOUNT,
      region: app.node.tryGetContext('region') || process.env.CDK_DEFAULT_REGION || 'us-east-1',
    },
  });

  // Website stack
  const { WebsiteStack } = require('./constructs/website_stack');
  new WebsiteStack(app, `Lingible-${environment.charAt(0).toUpperCase() + environment.slice(1)}-Website`, {
    description: `Lingible Website - ${environment.charAt(0).toUpperCase() + environment.slice(1)} Environment`,
    environment: environment,
    env: {
      account: app.node.tryGetContext('account') || process.env.CDK_DEFAULT_ACCOUNT,
      region: app.node.tryGetContext('region') || process.env.CDK_DEFAULT_REGION || 'us-east-1',
    },
  });
} else {
  // Hosted zones only deployment
  const { HostedZonesStack } = require('./constructs/hosted_zones_stack');
  new HostedZonesStack(app, `Lingible-${environment.charAt(0).toUpperCase() + environment.slice(1)}-HostedZones`, {
    description: `Lingible Hosted Zones - ${environment.charAt(0).toUpperCase() + environment.slice(1)} Environment`,
    environment: environment,
    env: {
      account: app.node.tryGetContext('account') || process.env.CDK_DEFAULT_ACCOUNT,
      region: app.node.tryGetContext('region') || process.env.CDK_DEFAULT_REGION || 'us-east-1',
    },
  });
}

// Add tags to all resources
cdk.Tags.of(app).add('Application', 'Lingible');
cdk.Tags.of(app).add('Environment', environment);
cdk.Tags.of(app).add('ManagedBy', 'CDK');
